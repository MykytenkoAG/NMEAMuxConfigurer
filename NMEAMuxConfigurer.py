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
        frame1 = tk.Frame(root, padx=10, pady=10)
        frame1.pack(fill="x")

        self.com_label = tk.Label(frame1, text="COM Port:")
        self.com_label.pack(side="left")

        self.com_combobox = ttk.Combobox(frame1, values=self.get_com_ports(), state="readonly")
        self.com_combobox.pack(side="left", padx=5)

        self.connect_button = tk.Button(frame1, text="Открыть", command=self.toggle_connection)
        self.connect_button.pack(side="left", padx=5)

        self.send_mkhalt_button = tk.Button(frame1, text="$MKHALT", command=self.send_mkhalt, state="disabled")
        self.send_mkhalt_button.pack(side="left", padx=5)

        # 2. Ввод текста и кнопка отправки
        frame2 = tk.Frame(root, padx=10, pady=10)
        frame2.pack(fill="x")

        self.input_entry = tk.Entry(frame2, width=50)
        self.input_entry.pack(side="left", padx=5)

        self.send_text_button = tk.Button(frame2, text="Отправить", command=self.send_text, state="disabled")
        self.send_text_button.pack(side="left", padx=5)

        # 3. Поле для приема данных
        frame3 = tk.Frame(root, padx=10, pady=10)
        frame3.pack(fill="both", expand=True)

        self.output_text = tk.Text(frame3, height=10, state="disabled")
        self.output_text.pack(fill="both", expand=True)

        # 4. Пустая секция
        frame4 = tk.Frame(root, height=50, padx=10, pady=10, bg="lightgray")
        frame4.pack(fill="both", expand=True)

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
