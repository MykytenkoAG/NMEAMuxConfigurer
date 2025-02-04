import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading

class SerialApp:
    def __init__(self, root):
        self.root = root
        self.root.title("COM Port Viewer")
        
        # Переменные
        self.serial_port = None
        self.running = False

        # 1. Выбор COM-порта и кнопка отправки $MKHALT
        frame1 = tk.Frame(root, padx=10, pady=5)
        frame1.pack(fill="x")

        self.com_label = tk.Label(frame1, text="COM Port:")
        self.com_label.pack(side="left")

        self.com_combobox = ttk.Combobox(frame1, values=self.get_com_ports(), state="readonly")
        self.com_combobox.pack(side="left", padx=5)

        self.connect_button = tk.Button(frame1, text="Открыть", command=self.toggle_connection)
        self.connect_button.pack(side="left", padx=5)

        self.send_mkhalt_button = tk.Button(frame1, text="Отправить $MKHALT", command=self.send_mkhalt, state="disabled")
        self.send_mkhalt_button.pack(side="left", padx=5)

        # 2. Ввод текста и кнопка отправки
        frame2 = tk.Frame(root, padx=10, pady=5)
        frame2.pack(fill="x")

        self.input_entry = tk.Entry(frame2, width=50)
        self.input_entry.pack(side="left", padx=5)

        self.send_text_button = tk.Button(frame2, text="Отправить", command=self.send_text, state="disabled")
        self.send_text_button.pack(side="left", padx=5)

        # 3. Поле для приема данных
        frame3 = tk.Frame(root, padx=10, pady=5)
        frame3.pack(fill="both", expand=True)

        self.output_text = tk.Text(frame3, height=10, state="disabled")
        self.output_text.pack(fill="both", expand=True)

        # 4.1 Кнопки "Канал 1" – "Канал 8"
        self.channel_frame = tk.Frame(root)
        self.channel_frame.pack(fill="x", pady=5)

        for i in range(1, 9):
            btn = tk.Button(self.channel_frame, text=f"Канал {i}", width=10)
            btn.pack(side="left", padx=2)

        # 4.2 Выбор скорости и поле "Период"
        self.config_frame = tk.Frame(root)
        self.config_frame.pack(fill="x", pady=5)

        self.speed_label = tk.Label(self.config_frame, text="Скорость:")
        self.speed_label.pack(side="left")

        self.speed_combobox = ttk.Combobox(self.config_frame, values=["4800", "9600", "38400", "115200"], state="readonly")
        self.speed_combobox.pack(side="left", padx=5)
        self.speed_combobox.current(1)  # По умолчанию 9600

        self.period_label = tk.Label(self.config_frame, text="Период:")
        self.period_label.pack(side="left", padx=10)

        self.period_entry = tk.Entry(self.config_frame, width=10)
        self.period_entry.pack(side="left")

        # 4.3 Список NMEA 0183 предложений с 5 чекбоксами в строке и прокруткой
        self.nmea_frame = tk.Frame(root)
        self.nmea_frame.pack(fill="both", expand=True, padx=10, pady=5)

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

        # Заголовок таблицы
        header_frame = tk.Frame(self.nmea_scrollable_frame)
        header_frame.pack(fill="x", pady=2)
        tk.Label(header_frame, text="Sentence ID", width=20, anchor="w").pack(side="left", padx=5)
        for i in range(1, 6):
            tk.Label(header_frame, text=f"Опция {i}", width=10).pack(side="left")

        # Данные NMEA
        self.nmea_sentences = [
            "GGA", "GLL", "GSA", "GSV", "RMC", "VTG", "ZDA", "HDG", "HDT", "DBT"
        ]

        self.nmea_vars = []
        for sentence in self.nmea_sentences:
            row_frame = tk.Frame(self.nmea_scrollable_frame)
            row_frame.pack(fill="x", pady=2)

            tk.Label(row_frame, text=sentence, width=20, anchor="w").pack(side="left", padx=5)

            row_vars = []
            for _ in range(5):
                var = tk.BooleanVar()
                row_vars.append(var)
                chk = tk.Checkbutton(row_frame, variable=var)
                chk.pack(side="left", padx=5)

            self.nmea_vars.append(row_vars)

    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

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
            self.serial_port = serial.Serial(port, baudrate=9600, timeout=1)
            self.running = True
            self.send_mkhalt_button.config(state="normal")
            self.send_text_button.config(state="normal")
            self.connect_button.config(text="Закрыть")
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
            self.serial_port.write(b"$MKHALT\n")

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

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialApp(root)
    root.mainloop()
