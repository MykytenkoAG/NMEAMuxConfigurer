import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import os
import time
from ParseFiles import parse_mkprg_file, write_mkprg_file

class SerialApp:
    def __init__(self, root):
        self.root = root
        self.data = parse_mkprg_file("configs/default_config.txt")
        self.checkbuttons = dict()
        self.root.title("MUX Configurer")
        
        self.serial_port = None
        self.lock = threading.Lock()
        self.running = False
        self.selected_channel = tk.IntVar(value=1)

        frame1 = tk.Frame(root, padx=10, pady=5)
        frame1.pack(fill="x")

        self.com_label = tk.Label(frame1, text="COM Port:")
        self.com_label.pack(side="left")

        self.com_combobox = ttk.Combobox(frame1, values=sorted(self.get_com_ports()), state="readonly", width=10)
        self.com_combobox.pack(side="left", padx=5)

        self.connect_button = tk.Button(frame1, text="Open", command=self.toggle_connection)
        self.connect_button.pack(side="left", padx=5)

        self.send_mkhalt_button = tk.Button(frame1, text="HALT", command=self.send_mkhalt, state="disabled")
        self.send_mkhalt_button.pack(side="left", padx=5)

        self.download_from_mux = tk.Button(frame1, text="Read from MUX", command=self.download_config)
        self.download_from_mux.pack(side="left", padx=5)
        
        self.upload_to_mux = tk.Button(frame1, text="Write to MUX", command=self.upload_config)
        self.upload_to_mux.pack(side="left", padx=5)

        frame2 = tk.Frame(root, padx=10, pady=5)
        frame2.pack(fill="x")

        self.input_entry = tk.Entry(frame2, width=40)
        self.input_entry.pack(side="left", padx=5, fill="x", expand=True)

        self.send_text_button = tk.Button(frame2, text="Send", command=self.send_text, state="disabled")
        self.send_text_button.pack(side="left", padx=5, fill="x")

        frame3 = tk.Frame(root, padx=10, pady=5)
        frame3.pack(fill="both", expand=True)

        self.output_text = tk.Text(frame3, height=10, state="disabled")
        self.output_text.pack(fill="both", expand=True)

        self.channel_frame = tk.LabelFrame(root, text="Channel selection")
        self.channel_frame.pack(fill="x", pady=5, padx=10)

        for i in range(1, 9):
            rb = ttk.Radiobutton(self.channel_frame, text=f"Channel {i}", variable=self.selected_channel, value=i, command=self.change_channel)
            rb.pack(side="left", padx=5)

        self.config_frame = tk.Frame(root)
        self.config_frame.pack(fill="x", pady=5)

        self.speed_label = tk.Label(self.config_frame, text="Baudrate:")
        self.speed_label.pack(side="left")

        self.baudrates = ["4800", "9600", "38400", "115200"]
        self.speed_combobox = ttk.Combobox(self.config_frame, values=self.baudrates, state="readonly", width=7)
        self.speed_combobox.pack(side="left", padx=5)
        self.speed_combobox.bind("<<ComboboxSelected>>", self.change_baudrate)

        for i in range(len(self.baudrates)):
            if self.baudrates[i] == self.data[0]["B"]:
                self.speed_combobox.current(i)

        self.period_label = tk.Label(self.config_frame, text="Period:")
        self.period_label.pack(side="left", padx=10)

        self.periods = ["0.01", "0.1", "0.5", "1", "2"]
        self.period_combobox = ttk.Combobox(self.config_frame, values=self.periods, state="readonly", width=5)
        self.period_combobox.pack(side="left")
        self.period_combobox.bind("<<ComboboxSelected>>", self.change_period)

        for i in range(len(self.periods)):
            if self.periods[i] == self.data[0]["T"]:
                self.period_combobox.current(i)

        self.period_label = tk.Label(self.config_frame, text="s")
        self.period_label.pack(side="left", padx=10)

        self.nmea_frame = tk.Frame(root)
        self.nmea_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.header_frame = tk.Frame(self.nmea_frame)
        self.header_frame.pack(fill="x")

        headers = ["Sentence ID", "In", "Out", "Conv", "Forced", "Calc"]
        for col, header in enumerate(headers):
            label = tk.Label(self.header_frame, text=header, anchor="center", relief="solid", borderwidth=1)
            label.grid(row=0, column=col, padx=5, pady=2, sticky="nsew")
            self.header_frame.grid_columnconfigure(col, weight=1)

        # Заголовки таблицы
        headers = ["Sentence ID", "In", "Out", "Conv", "Forced", "Calc"]
        for col, header in enumerate(headers):
            label = tk.Label(self.header_frame, text=header, width=15, anchor="center", relief="solid", borderwidth=1)
            label.grid(row=0, column=col, padx=5, pady=2, sticky="nsew")

        # Настройка одинаковой ширины столбцов для заголовков
        for col in range(len(headers)):
            self.header_frame.grid_columnconfigure(col, weight=1, uniform="column")

        # Фрейм для содержимого таблицы (прокручивается)
        self.nmea_canvas = tk.Canvas(self.nmea_frame)
        self.nmea_scrollbar = ttk.Scrollbar(self.nmea_frame, orient="vertical", command=self.nmea_canvas.yview)

        self.nmea_scrollable_frame = tk.Frame(self.nmea_canvas)
        self.nmea_scrollable_frame.bind(
            "<Configure>", lambda e: self.nmea_canvas.configure(scrollregion=self.nmea_canvas.bbox("all"))
        )

        self.nmea_canvas.create_window((0, 0), window=self.nmea_scrollable_frame, anchor="nw")
        self.nmea_canvas.configure(yscrollcommand=self.nmea_scrollbar.set)

        self.nmea_canvas.pack(side="left", fill="both", expand=True)
        self.nmea_scrollbar.pack(side="right", fill="y")

        # Настройка одинаковой ширины столбцов для содержимого
        for col in range(len(headers)):
            self.nmea_scrollable_frame.grid_columnconfigure(col, weight=1, uniform="column")

        # Создание таблицы с чекбоксами
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
                var = tk.BooleanVar()
                row_vars.append(var)
                chk = tk.Checkbutton(
                    self.nmea_scrollable_frame, variable=var,
                    command=lambda v=var, id=col-1, sentence=sentence, channel_num=0: self.change_sentence_mode(v, channel_num, sentence, id)
                )
                chk.grid(row=row, column=col, padx=5, pady=2, sticky="nsew")
                self.checkbuttons[sentence].append(chk)

                # Установка состояния чекбокса на основе данных конфигурации
                if self.data[0][sentence][col-1] == "1":
                    chk.select()

            self.nmea_vars.append(row_vars)

    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return sorted([port.device for port in ports])
    
    def toggle_connection(self):
        if self.serial_port:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        port = self.com_combobox.get()
        if not port:
            return

        try:
            self.serial_port = serial.Serial(port, baudrate=38400, timeout=1)
            self.running = True
            self.send_mkhalt_button.config(state="normal")
            self.send_text_button.config(state="normal")
            self.connect_button.config(text="Close")
            threading.Thread(target=self.read_from_port, daemon=True).start()
        except serial.SerialException as e:
            self.log_to_output(f"Ошибка: {e}")

    def disconnect(self):
        self.running = False
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None
        self.send_mkhalt_button.config(state="disabled")
        self.send_text_button.config(state="disabled")
        self.connect_button.config(text="Открыть")

    def send_mkhalt(self):
        if self.serial_port:
            self.serial_port.write(b"$MKHALT\n$MKHALT\n")

    def send_text(self):
        if self.serial_port:
            text = self.input_entry.get().strip()
            if text:
                self.serial_port.write((text + "\n").encode())

    def read_from_port(self):
        while self.running:
            if self.serial_port and self.serial_port.in_waiting:
                try:
                    data = self.serial_port.readline().decode().strip()
                    if data:
                        self.log_to_output(data)
                except UnicodeDecodeError:
                    pass

    def log_to_output(self, message):
        self.output_text.config(state="normal")
        self.output_text.insert("end", message + "\n")
        self.output_text.config(state="disabled")
        self.output_text.yview("end")

    # Изменение скорости работы канала
    def change_baudrate(self, event):
        data_ind = self.selected_channel.get()-1
        self.data[data_ind]["B"]=self.speed_combobox.get()

    # Изменение периода отправки сообщений
    def change_period(self, event):
        data_ind = self.selected_channel.get()-1
        self.data[data_ind]["T"]=self.period_combobox.get()

    # Изменение настроек сообщения
    def change_sentence_mode(self, var, channel_num, sentence, cb_id):
        sentence_mode = self.data[channel_num][sentence]
        if(var.get()):
            sentence_mode=sentence_mode[:cb_id]+"1"+sentence_mode[cb_id+1:]
        else:
            sentence_mode=sentence_mode[:cb_id]+"0"+sentence_mode[cb_id+1:]
        self.data[channel_num][sentence] = sentence_mode
        print(f"{sentence} : {self.data[channel_num][sentence]}")

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
                    if(self.data[data_ind][key][i]=="1"):
                        self.checkbuttons[key][i].select()
                    else:
                        self.checkbuttons[key][i].deselect()

    # Загрузить конфигурацию с мультиплексора
    def download_config(self, filename="configs/current_config.txt"):
        if not self.serial_port or not self.serial_port.is_open:
            self.log_to_output("Ошибка: COM-порт не открыт")
            return

        try:
            with self.lock:
                self.serial_port.reset_input_buffer()
                self.serial_port.write(b"$MKPRG,CFG:B\n")
                start_time = time.time()
                response = ""
                while "ready :" not in response:
                    if time.time() - start_time > 5:
                        self.log_to_output("Превышен интервал ожидания")
                        return
                    response += self.serial_port.read(50).decode(errors="ignore")

                self.serial_port.write(b"\n")

        except serial.SerialException as e:
            self.log_to_output(f"Ошибка работы с COM-портом: {e}")

    # Загрузить конфигурацию в мультиплексор
    def upload_config(self):
        new_config = "configs/new_config.txt"
        write_mkprg_file(self.data, new_config)

        if not self.serial_port or not self.serial_port.is_open:
            print("Ошибка: COM-порт не открыт")
            return

        try:
            with open(new_config, "r", encoding="utf-8") as file:
                lines = file.readlines()

            for line in lines:
                self.serial_port.write((line.strip() + "\r\n").encode())  # Отправляем строку с CRLF
                time.sleep(0.1)  # Даем устройству время обработать данные
                print(f"Отправлено: {line.strip()}")  # Для отладки

            print("Файл успешно отправлен через COM-порт")

        except FileNotFoundError:
            print(f"Ошибка: файл {new_config} не найден")
        except serial.SerialException as e:
            print(f"Ошибка работы с COM-портом: {e}")

if __name__ == "__main__":    
    root = tk.Tk()
    app = SerialApp(root)
    root.mainloop()
