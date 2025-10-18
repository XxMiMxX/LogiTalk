
import base64
import os
from socket import *
from customtkinter import *
from tkinter import filedialog as tk_filedialog
from PIL import Image

class MainWindow(CTk):
    def __init__(self):
        super().__init__()
        self.title("Logi Talk")
        self.geometry("600x400")
        self.minsize(400, 300)

        self.username = "User"
        self.menu_show_speed = 0  # мгновенное открытие
        self.max_frame_width = 200
        self.frame_width = 0
        self.is_show_menu = False

        # боковое меню
        self.frame = CTkFrame(self, width=0)
        self.frame.pack(side="left", fill="y")
        self.frame.pack_propagate(False)
        CTkLabel(self.frame, text='Ваше ім’я:').pack(pady=10)
        self.entry = CTkEntry(self.frame, placeholder_text="Введіть нік")
        self.entry.pack(pady=5)
        CTkButton(self.frame, text="💾 Зберегти нік", command=self.save_username).pack(pady=10)
        self.label_theme = CTkOptionMenu(self.frame, values=['Темна', 'Світла'], command=self.change_theme)
        self.label_theme.pack(side="bottom", pady=20)

        # основное окно чата
        self.chat_frame = CTkFrame(self)
        self.chat_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.btn = CTkButton(self, text="▶️", command=self.toggle_show_menu, width=30)
        self.btn.place(x=0, y=0)

        # скроллируемое поле сообщений
        self.messages_container = CTkScrollableFrame(self.chat_frame)
        self.messages_container.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        # нижняя панель
        self.bottom_frame = CTkFrame(self.chat_frame)
        self.bottom_frame.pack(fill="x", pady=(0, 0))
        self.message_input = CTkEntry(self.bottom_frame, placeholder_text='Введіть повідомлення:')
        self.message_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.send_button = CTkButton(self.bottom_frame, text='📩', width=40, command=self.send_message)
        self.send_button.pack(side="right", padx=(5, 0))
        self.photo_button = CTkButton(self.bottom_frame, text='📷', width=40, command=self.open_file_menu)
        self.photo_button.pack(side="right", padx=(5, 0))
        self.emoji_button = CTkButton(self.bottom_frame, text='😊', width=40, command=self.toggle_emoji_menu)
        self.emoji_button.pack(side="right", padx=(5, 0))

        self.emoji_frame = None
        self.file_frame = None
        self.images_cache = []

        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect(("2.tcp.eu.ngrok.io", 16202))
            hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
            self.sock.send(hello.encode('utf-8'))
            threading.Thread(target=self.recv_message, daemon=True).start()
        except Exception as e:
            self.add_message(f"❌ Не вдалося підключитися: {e}")

    def toggle_show_menu(self):
        self.is_show_menu = not self.is_show_menu
        if self.is_show_menu:
            self.frame.configure(width=self.max_frame_width)
            self.btn.configure(text='◀️')
        else:
            self.frame.configure(width=0)
            self.btn.configure(text='▶️')

    def change_theme(self, value):
        set_appearance_mode('dark' if value == 'Темна' else 'light')

    def send_message(self):
        message = self.message_input.get().strip()
        if message:
            self.add_message(f"{self.username}: {message}")
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.sock.sendall(data.encode())
            except:
                pass
        self.message_input.delete(0, END)

    def send_image(self, file_path):
        if not file_path:
            return
        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            filename = os.path.basename(file_path)
            packet = f"IMAGE@{self.username}@{filename}@{image_data}\n"
            self.sock.sendall(packet.encode())
            self.add_image_message(f"{self.username} 📷:", file_path)
        except Exception as e:
            self.add_message(f"❌ Помилка при надсиланні зображення: {e}")

    def open_file_menu(self):
        if self.file_frame and self.file_frame.winfo_ismapped():
            self.file_frame.pack_forget()
            return
        if self.emoji_frame and self.emoji_frame.winfo_ismapped():
            self.emoji_frame.pack_forget()
        self.file_frame = CTkFrame(self.chat_frame)
        CTkLabel(self.file_frame, text="📷 Виберіть дію").pack(pady=5)
        CTkButton(self.file_frame, text="📁 Вибрати зображення", command=self.choose_file).pack(pady=3)
        CTkButton(self.file_frame, text="❌ Закрити", command=lambda: self.file_frame.pack_forget()).pack(pady=3)
        self.file_frame.pack(fill="x", pady=(0, 5))

    def choose_file(self):
        file_path = tk_filedialog.askopenfilename(
            title="Виберіть зображення",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")]
        )
        self.file_frame.pack_forget()
        if file_path:
            self.send_image(file_path)

    def recv_message(self):
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode(errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())
            except:
                break
        self.sock.close()

    def handle_line(self, line):
        if not line:
            return
        parts = line.split("@", 3)
        msg_type = parts[0]
        if msg_type == "TEXT" and len(parts) >= 3:
            author, message = parts[1], parts[2]
            self.add_message(f"{author}: {message}")
        elif msg_type == "IMAGE" and len(parts) >= 4:
            author, filename, img_data = parts[1], parts[2], parts[3]
            os.makedirs("received_images", exist_ok=True)
            save_path = os.path.join("received_images", filename)
            try:
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                self.add_image_message(f"{author} 📷:", save_path)
            except Exception as e:
                self.add_message(f"❌ Не вдалося зберегти зображення від {author}: {e}")
        else:
            self.add_message(line)

    def add_message(self, text):
        lbl = CTkLabel(self.messages_container, text=text, anchor="w", justify="left", wraplength=450)
        lbl.pack(fill="x", pady=2, padx=5, anchor="w")

    def add_image_message(self, author, img_path):
        self.add_message(author)
        try:
            img = Image.open(img_path)
            img.thumbnail((250, 250))
            ctk_img = CTkImage(light_image=img, dark_image=img, size=img.size)
            self.images_cache.append(ctk_img)
            lbl = CTkLabel(self.messages_container, image=ctk_img, text="")
            lbl.pack(pady=5, padx=10, anchor="w")
        except Exception as e:
            self.add_message(f"❌ Помилка відображення зображення: {e}")

    def save_username(self):
        new_name = self.entry.get().strip()
        if new_name:
            old_name = self.username
            self.username = new_name
            try:
                msg = f"TEXT@{self.username}@[SYSTEM] {old_name} змінив(ла) ім’я на {self.username}\n"
                self.sock.send(msg.encode('utf-8'))
            except:
                pass
            self.add_message(f"✅ Нік змінено на {self.username}")

    def toggle_emoji_menu(self):
        if self.emoji_frame and self.emoji_frame.winfo_ismapped():
            self.emoji_frame.pack_forget()
        else:
            self.show_emoji_menu()

    def show_emoji_menu(self):
        if self.emoji_frame:
            self.emoji_frame.pack_forget()
        if self.file_frame and self.file_frame.winfo_ismapped():
            self.file_frame.pack_forget()
        self.emoji_frame = CTkFrame(self.chat_frame)
        emojis = ["😊", "😂", "❤️", "🔥", "👍", "🎉", "😎", "🙃", "😭", "😡", "🤔", "🥰", "😴", "😅", "😇"]
        for i, emoji in enumerate(emojis):
            btn = CTkButton(self.emoji_frame, text=emoji, width=35, command=lambda e=emoji: self.add_emoji(e))
            btn.grid(row=i//8, column=i%8, padx=2, pady=2)
        self.emoji_frame.pack(fill="x", pady=(0, 5))

    def add_emoji(self, emoji):
        self.message_input.insert(END, emoji)
        if self.emoji_frame:
            self.emoji_frame.pack_forget()

if __name__ == "__main__":
    set_appearance_mode("dark")
    win = MainWindow()
    win.mainloop()

