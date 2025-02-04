import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import os
import tempfile
import time
from ParseFiles import parse_mkprg_file, write_mkprg_file

class SerialApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MUX Configurator")
        self.root.resizable(True, True)  # Разрешаем изменение размеров окна

        # Временный файл для хранения конфигурации
        self.temp_config_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w+")
        self.temp_config_file.close()

        self.serial_port = None
        self.lock = threading.Lock()
        self.running = False

        self.data = []
        self.checkbuttons = dict()
        self.nmea_vars = []
        self.selected_channel = tk.IntVar(value=1)

        # Таблица с элементами управления (3 строки, 10 столбцов)
        control_frame = tk.Frame(root, padx=10, pady=5)
        control_frame.pack(fill="x")

        # Строка 0
        # Выбор COM-порта
        tk.Label(control_frame, text="COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.combobox_COM_port = ttk.Combobox(control_frame, values=sorted(self.get_com_ports()), state="readonly", width=15)
        self.combobox_COM_port.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Выбор скорости работы
        tk.Label(control_frame, text="Baudrate:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.baudrates = ["4800", "9600", "38400", "115200"]
        self.combobox_COM_baudrate = ttk.Combobox(control_frame, values=self.baudrates, state="readonly", width=10)
        self.combobox_COM_baudrate.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.combobox_COM_baudrate.current(2)  # По умолчанию 38400

        # Кнопка подключения к порту
        self.btn_connect = tk.Button(control_frame, text="Open", command=self.toggle_connection, width=10)
        self.btn_connect.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Кнопка MKHALT
        self.btn_mkhalt = tk.Button(control_frame, text="HALT", command=self.send_mkhalt, state="disabled", width=10)
        self.btn_mkhalt.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        # Кнопка Download from MUX
        self.btn_read_from_mux = tk.Button(control_frame, text="Read from MUX", command=self.read_config, state="disabled", width=25)
        self.btn_read_from_mux.grid(row=0, column=6, columnspan=2, padx=5, pady=5, sticky="w")

        # Кнопка Upload to MUX
        self.btn_write_to_mux = tk.Button(control_frame, text="Write to MUX", command=self.write_config, state="disabled", width=25)
        self.btn_write_to_mux.grid(row=0, column=8, columnspan=2, padx=5, pady=5, sticky="w")

        # Строка 1
        # Поле с отображением пути к выбранному файлу
        self.entry_conf_file = tk.Entry(control_frame, width=50)
        self.entry_conf_file.grid(row=1, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")

        # Кнопка Browse
        self.btn_browse = tk.Button(control_frame, text="Browse", command=self.browse_file, state="disabled", width=10)
        self.btn_browse.grid(row=1, column=5, padx=5, pady=5, sticky="w")

        # Кнопка Update config from file
        self.btn_update_config_from_file = tk.Button(control_frame, text="Update config from file", command=self.update_config_from_file, state="disabled", width=25)
        self.btn_update_config_from_file.grid(row=1, column=6, columnspan=2, padx=5, pady=5, sticky="nsew")

        # Кнопка Download config to PC
        self.btn_download_config_to_PC = tk.Button(control_frame, text="Download config to PC", command=self.download_config_file, state="disabled", width=25)
        self.btn_download_config_to_PC.grid(row=1, column=8, columnspan=2, padx=5, pady=5, sticky="nsew")

        # Строка 2
        # Поле для ручного ввода команд
        self.entry_cmd = tk.Entry(control_frame, width=50)
        self.entry_cmd.grid(row=2, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")
        self.entry_cmd.bind("<Return>", self.handle_enter_key)

        # Кнопка Send
        self.btn_send = tk.Button(control_frame, text="Send", command=self.send_text, state="disabled", width=10)
        self.btn_send.grid(row=2, column=5, padx=5, pady=5, sticky="w")

        # Кнопка Reboot
        self.btn_reboot = tk.Button(control_frame, text="Reboot", command=self.reboot_system, state="disabled", width=10)
        self.btn_reboot.grid(row=2, column=6, padx=5, pady=5, sticky="nsew")

        # Кнопка Read Log
        self.btn_read_log = tk.Button(control_frame, text="Read Log", command=self.read_log, state="disabled", width=10)
        self.btn_read_log.grid(row=2, column=7, padx=5, pady=5, sticky="nsew")

        # Кнопка Clear Log
        self.btn_clear_log = tk.Button(control_frame, text="Clear Log", command=self.clear_log, state="disabled", width=10)
        self.btn_clear_log.grid(row=2, column=8, padx=5, pady=5, sticky="nsew")

        # Кнопка Clear Output
        self.btn_clear_output = tk.Button(control_frame, text="Clear Output", command=self.clear_output, width=10)
        self.btn_clear_output.grid(row=2, column=9, padx=5, pady=5, sticky="nsew")

        # Фрейм с выходом COM-порта
        output_frame = tk.Frame(root, padx=10, pady=5)
        output_frame.pack(fill="both", expand=True)

        self.output_text = tk.Text(output_frame, height=7, state="disabled")
        self.output_text.pack(fill="both", expand=True)

        # Конфигурация по умолчанию
        self.data = [
            {"ChannelNumber": "1", "B": "38400", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
            {"ChannelNumber": "2", "B": "38400", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
            {"ChannelNumber": "3", "B": "38400", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
            {"ChannelNumber": "4", "B": "38400", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
            {"ChannelNumber": "5", "B": "4800", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
            {"ChannelNumber": "6", "B": "4800", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
            {"ChannelNumber": "7", "B": "4800", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
            {"ChannelNumber": "8", "B": "4800", "T": "1","GGA":"11100","GNS":"11100","GLL":"11100","RMC":"11100","VTG":"11100","ZDA":"11100","DTM":"11000","BOD":"11000","BWC":"11000","BWR":"11000","BWW":"11000","GBS":"11000","GLC":"11000","GSA":"11000","GSV":"11000","RMA":"11000","RMB":"11000","RTE":"11000","Rnn":"11000","WCV":"11000","WNC":"11000","WNR":"11000","WPL":"11000","XTE":"11000","ZTG":"11000","VDO":"11100","VDM":"11000","HDT":"11110","HDG":"11000","HDM":"11000","ROT":"11000","VBW":"11000","VHW":"11000","VLW":"11000","VDR":"11000","DBK":"11000","DBS":"11000","DBT":"11000","DPT":"11000","MDA":"11000","MWD":"11000","MWV":"11000","MTW":"11000","XDR":"11000","VWR":"11000","VWT":"11000","RSD":"11000","TLL":"11000","TTM":"11000","RSA":"11000","AAM":"11000","APA":"11000","APB":"11000","ALR":"11000","EVE":"11000","TXT":"11000","OTHER":"11000","TID": "1"},
                        ]

        # Фрейм с выбором канала
        self.channel_frame = tk.LabelFrame(root, text="Channel selection")
        self.channel_frame.pack(fill="x", pady=5, padx=10)

        for i in range(1, 9):
            rb = ttk.Radiobutton(self.channel_frame, text=f"Channel {i}", variable=self.selected_channel, value=i, command=self.change_channel)
            rb.pack(side="left", padx=5)

        # Фрейм с настройкой скорости работы канала и периодом отправки сообщений
        self.config_frame = tk.Frame(root)
        self.config_frame.pack(fill="x", padx=10, pady=5)

        self.speed_label = tk.Label(self.config_frame, text="Baudrate:")
        self.speed_label.pack(side="left")

        self.baudrates = ["4800", "9600", "38400", "115200"]
        self.speed_combobox = ttk.Combobox(self.config_frame, values=self.baudrates, state="readonly", width=7)
        self.speed_combobox.pack(side="left", padx=5)
        self.speed_combobox.bind("<<ComboboxSelected>>", self.change_channel_baudrate)

        for i in range(len(self.baudrates)):
            if self.baudrates[i] == self.data[0]["B"]:
                self.speed_combobox.current(i)

        self.period_label = tk.Label(self.config_frame, text="Period:")
        self.period_label.pack(side="left", padx=10)

        self.periods = ["0.01", "0.1", "0.5", "1", "2"]
        self.period_combobox = ttk.Combobox(self.config_frame, values=self.periods, state="readonly", width=5)
        self.period_combobox.pack(side="left")
        self.period_combobox.bind("<<ComboboxSelected>>", self.change_channel_period)

        for i in range(len(self.periods)):
            if self.periods[i] == self.data[0]["T"]:
                self.period_combobox.current(i)

        self.period_label = tk.Label(self.config_frame, text="s")
        self.period_label.pack(side="left", padx=10)

        # Фрейм с настройками сообщений
        self.nmea_frame = tk.Frame(root)
        self.nmea_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Заголовки таблицы и чекбоксы объединены в одну таблицу
        self.nmea_canvas = tk.Canvas(self.nmea_frame)
        self.nmea_scrollbar = ttk.Scrollbar(self.nmea_frame, orient="vertical", command=self.nmea_canvas.yview)
        self.nmea_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.nmea_scrollable_frame = tk.Frame(self.nmea_canvas)
        self.nmea_scrollable_frame.bind(
            "<Configure>", lambda e: self.nmea_canvas.configure(scrollregion=self.nmea_canvas.bbox("all"))
        )
        self.nmea_canvas.create_window((0, 0), window=self.nmea_scrollable_frame, anchor="nw")
        self.nmea_canvas.configure(yscrollcommand=self.nmea_scrollbar.set)
        self.nmea_canvas.pack(side="left", fill="both", expand=True)
        self.nmea_scrollbar.pack(side="right", fill="y")

        # Заголовки таблицы
        headers = ["Sentence ID", "In", "Out", "Conv", "Forced", "Calc"]
        for col, header in enumerate(headers):
            label = tk.Label(self.nmea_scrollable_frame, text=header, width=15, anchor="center", relief="solid", borderwidth=1)
            label.grid(row=0, column=col, padx=5, pady=2, sticky="w")
            self.nmea_scrollable_frame.grid_columnconfigure(col, weight=1, uniform="column")
        
        if self.data is not None:
            self.create_checkboxes()

   # Создание таблицы чекбоксов
    def create_checkboxes(self):
        for widget in self.nmea_scrollable_frame.winfo_children():
            widget.destroy()

        self.nmea_sentences = [key for key in self.data[0].keys() if key not in {"ChannelNumber", "B", "T"}]
        self.nmea_vars = []
        self.checkbuttons = dict()

        for row, sentence in enumerate(self.nmea_sentences, start=1):
            # Sentence ID
            label = tk.Label(self.nmea_scrollable_frame, text=sentence, width=15, anchor="center", relief="solid", borderwidth=1)
            label.grid(row=row, column=0, padx=5, pady=2, sticky="nsew")

            # Чекбоксы для каждого столбца
            row_vars = []
            self.checkbuttons[sentence] = []
            for col in range(1, 6):  # 5 столбцов: In, Out, Conv, Forced, Calc
                if sentence == "TID" and col > 1:
                    continue
                var = tk.BooleanVar()
                row_vars.append(var)
                chk = tk.Checkbutton(
                    self.nmea_scrollable_frame, variable=var,
                    command=lambda v=var, sentence=sentence, id=col-1: self.change_sentence_mode(v, sentence, id)
                )
                chk.grid(row=row, column=col, padx=5, pady=2, sticky="nsew")
                self.checkbuttons[sentence].append(chk)

                # Установка состояния чекбокса на основе данных конфигурации
                if self.data[0][sentence][col-1] == "1":
                    chk.select()

            self.nmea_vars.append(row_vars)

    # Для блокировки/разблокировки кнопок
    def set_button_states(self, state):
        buttons = [
            self.btn_mkhalt, self.btn_read_from_mux, self.btn_write_to_mux,
            self.btn_browse, self.btn_download_config_to_PC,
            self.btn_send, self.btn_reboot, self.btn_read_log, self.btn_clear_log
        ]
        for button in buttons:
            button.config(state=state)

    # Получение списка доступных COM-портов
    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return sorted([port.device for port in ports])
    
    # Открытие/закрытие соединения
    def toggle_connection(self):
        if self.serial_port:
            self.disconnect()
        else:
            self.connect()

    # Содинение
    def connect(self):
        port = self.combobox_COM_port.get()
        if not port:
            return
        try:
            self.serial_port = serial.Serial(port, baudrate=self.combobox_COM_baudrate.get(), timeout=1)
            self.running = True
            # Разблокировка кнопок
            self.set_button_states("normal")
            self.btn_connect.config(text="Close")
            # Запуск функции чтения из порта выполняется в отдеьном потоке
            threading.Thread(target=self.read_from_port, daemon=True).start()
        except serial.SerialException as e:
            self.log_to_output(f"Ошибка: {e}")

    # Закрытие соединения
    def disconnect(self):
        self.running = False
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None
        # Блокировка кнопок
        self.set_button_states("disabled")
        self.btn_connect.config(text="Open")

    # Чтение данных из порта и их отображение
    def read_from_port(self):
        while self.running:
            if self.serial_port and self.serial_port.in_waiting:
                try:
                    data = self.serial_port.readline().decode().strip()
                    if data:
                        self.log_to_output(data)
                except UnicodeDecodeError:
                    pass

    # Добавление текста в поле output_text
    def log_to_output(self, message):
        self.output_text.config(state="normal")
        self.output_text.insert("end", message + "\n")
        self.output_text.config(state="disabled")
        self.output_text.yview("end")

    # Очистка поля для отображения сообщений из COM-порта
    def clear_output(self):
        self.output_text.config(state="normal")
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state="disabled")

    # Отправка 2х команд $MKHALT для остановки приема сообщений по каналам 2..8
    def send_mkhalt(self):
        if self.serial_port:
            self.serial_port.write(b"$MKHALT\r\n")
            time.sleep(0.2)
            self.serial_port.write(b"$MKHALT\r\n")

    # Чтение журнала
    def read_log(self):
        if self.serial_port:
            self.serial_port.write(b"$MKPRG,LOG\r\n")

    # Очистка журнала
    def clear_log(self):
        if self.serial_port:
            self.serial_port.write(b"$MKPRG,LOGCLR:42\r\n")

    # Перезагрузка системы
    def reboot_system(self):
        if self.serial_port:
            self.serial_port.write(b"$RESET\r\n")

    # Отправка текста, набранного в поле ввода
    def send_text(self, event=None):
        if self.serial_port and self.serial_port.is_open:
            text = self.entry_cmd.get().strip()
            self.serial_port.write((text + "\r\n").encode("utf-8"))
            self.entry_cmd.delete(0, tk.END)

    # Обработка нажатия клавиши Enter
    def handle_enter_key(self, event):
        self.send_text()

    # НАСТРОКА МУЛЬТИПЛЕКСОРА -----------------------------------------------------------------------
    # Загрузить конфигурацию с мультиплексора
    def read_config(self):
        if not self.serial_port or not self.serial_port.is_open:
            self.log_to_output("Error: COM port not open")
            return
        try:
            with self.lock:
                self.serial_port.reset_input_buffer()
                self.serial_port.write(b"$MKPRG,CFG:B\n")
                self.log_to_output("$MKPRG,CFG:B\n")

                # Ждем первые данные (максимум 3 сек)
                timeout = time.time() + 3
                while self.serial_port.in_waiting == 0:
                    if time.time() > timeout:
                        self.log_to_output("Error: Device not responding")
                        return
                    time.sleep(0.1)

                self.serial_port.write(b"\n")

                # Чтение 8 строк с таймаутом
                lines = []
                for _ in range(8):
                    start_time = time.time()
                    data = b""
                    while time.time() - start_time < 2:  # Таймаут 2 секунды на строку
                        if self.serial_port.in_waiting > 0:
                            data += self.serial_port.read(self.serial_port.in_waiting)
                            if b"\n" in data:
                                break
                        time.sleep(0.1)

                    if not data:
                        self.log_to_output("Error: Timeout reading line")
                        return

                    line = data.decode(errors="ignore").strip()
                    if line:
                        lines.append(line)
                        self.log_to_output(line)
               
                # 5. Сохранение в файл
                # Склеивание строк с пробелами между ними
                config_text = "".join(lines).replace("Press ENTER when ready :", "").replace("\n","").replace("$","\n$")

                # Сохранение в файл
                with open(self.temp_config_file.name, "w", encoding="utf-8") as file:
                    file.write(config_text)

            self.data = parse_mkprg_file(self.temp_config_file.name)
            self.create_checkboxes()
            self.selected_channel.set(1)
            self.change_channel()

        except serial.SerialException as e:
            self.log_to_output(f"Ошибка работы с COM-портом: {e}")

    # Загрузить конфигурацию в мультиплексор
    def write_config(self):
        if not self.serial_port or not self.serial_port.is_open:
            self.log_to_output("Error: COM port not open")
            return

        try:
            # Запись данных во временный файл
            write_mkprg_file(self.data, self.temp_config_file.name)

            # Чтение из временного файла и отправка в COM-порт
            with open(self.temp_config_file.name, "r", encoding="utf-8") as file:
                for line in file:
                    self.serial_port.write((line.strip() + "\r\n").encode())
                    time.sleep(0.1)

        except Exception as e:
            self.log_to_output(f"Error: {e}")

    # Удаление временного файла при закрытии приложения
    def on_closing(self):
        if os.path.exists(self.temp_config_file.name):
            os.remove(self.temp_config_file.name)
        self.root.destroy()

    # Перерисовка всех параметров при изменении канала
    def change_channel(self):
        data_ind = self.selected_channel.get()-1
        # Перерисовка скорости
        for i in range(len(self.baudrates)):
            if(self.baudrates[i]==self.data[data_ind]["B"]):
                self.speed_combobox.current(i)
        # Перерисовка периода отправки
        for i in range(len(self.periods)):
            if(self.periods[i]==self.data[data_ind]["T"]):
                self.period_combobox.current(i)
        # Перерисовка настроек сообщений
        for key in self.data[0].keys():
            if(key not in {"ChannelNumber", "B", "T"}):
                for i in range(5):
                    if(key=="TID" and i!=0):
                        continue
                    if(self.data[data_ind][key][i]=="1"):
                        self.checkbuttons[key][i].select()
                    else:
                        self.checkbuttons[key][i].deselect()

    # Прокручивание таблицы с чекбоксами при прокручивании колесика мыши
    def _on_mousewheel(self, event):
        self.nmea_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # Изменение скорости работы канала
    def change_channel_baudrate(self, event):
        data_ind = self.selected_channel.get()-1
        self.data[data_ind]["B"]=self.speed_combobox.get()

    # Изменение периода отправки сообщений
    def change_channel_period(self, event):
        data_ind = self.selected_channel.get()-1
        self.data[data_ind]["T"]=self.period_combobox.get()

    # Изменение настроек сообщения
    def change_sentence_mode(self, var, sentence, cb_id):
        data_ind = self.selected_channel.get()-1
        sentence_mode = self.data[data_ind][sentence]
        if(var.get()):
            sentence_mode=sentence_mode[:cb_id]+"1"+sentence_mode[cb_id+1:]
        else:
            sentence_mode=sentence_mode[:cb_id]+"0"+sentence_mode[cb_id+1:]
        self.data[data_ind][sentence] = sentence_mode

    # Проверка файла на валидность
    def is_config_file_valid(self, filename):
        try:
            data = parse_mkprg_file(filename)  # Пытаемся разобрать файл
            if not isinstance(data, list) or len(data) != 8:  # Проверяем количество каналов
                return False
            for channel in data:  # Проверяем наличие обязательных ключей
                if not all(key in channel for key in ["ChannelNumber", "B", "T"]):
                    return False
            return True  # Файл корректен
        except Exception:
            return False  # Файл некорректен

    # Кнопка Browse
    def browse_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Select configuration file"
        )
        if filename:  # Если пользователь выбрал файл
            self.entry_conf_file.delete(0, tk.END)
            self.entry_conf_file.insert(0, filename)
            if self.is_config_file_valid(filename):  # Проверяем корректность файла
                self.btn_update_config_from_file.config(state="normal")  # Разблокируем кнопку
            else:
                self.btn_update_config_from_file.config(state="disabled")  # Блокируем кнопку
                messagebox.showerror("Error", "The file you selected is not in the correct format.")

    # Обновление конфигурации из файла
    def update_config_from_file(self):
        filename = self.entry_conf_file.get()
        if os.path.exists(filename):
            try:
                self.data = parse_mkprg_file(filename)  # Загружаем данные из файла
                self.create_checkboxes()
                self.selected_channel.set(1)
                self.change_channel()  # Обновляем интерфейс
                self.log_to_output(f"Configuration updated from file: {filename}")
            except Exception as e:
                self.log_to_output(f"Error loading file: {e}")

    # Скачать текущую конфигурацию
    def download_config_file(self):
        # Открываем диалоговое окно для выбора места сохранения и имени файла
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save configuration as"
        )
        if filename:  # Если пользователь выбрал файл
            try:
                write_mkprg_file(self.data, filename)  # Сохраняем конфигурацию
                self.log_to_output(f"Configuration saved to : {filename}")
            except Exception as e:
                self.log_to_output(f"Error saving file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
