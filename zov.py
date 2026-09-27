import os
import time
 
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
import scipy.io.wavfile as wavfile
 
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
 
 
FIREFOX_BINARY = r"C:\Program Files\Mozilla Firefox\firefox.exe"
GECKODRIVER_PATH = "geckodriver.exe"
DEFAULT_URL = "https://google.com"
 
LANGUAGE = "ru-RU"
 
 
# Голосовой движок 
 
class Voice:
 
    SAMPLE_RATE = 16000
    MIC_DEVICE = 1  
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 175)
        self.recognizer = sr.Recognizer()
 
    def say(self, text: str) -> None:
        print(f"[Ассистент]: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
 
    def _record(self, duration: int) -> sr.AudioData:
        try:
            recording = sd.rec(
                int(duration * self.SAMPLE_RATE),
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=self.MIC_DEVICE,
            )
            sd.wait()
            print("Максимальная громкость записи:", abs(recording).max())
            wavfile.write("debug.wav", self.SAMPLE_RATE, recording)
        except Exception as e:
            print(f"Ошибка записи звука: {e}")
            return sr.AudioData(b"\x00" * int(duration * self.SAMPLE_RATE) * 2, self.SAMPLE_RATE, 2)
        audio_bytes = recording.tobytes()
        return sr.AudioData(audio_bytes, self.SAMPLE_RATE, 2)  # 2 байта = 16 бит
 
    def listen(self, prompt: str = None, timeout: int = 6, phrase_time_limit: int = 6) -> str:
        if prompt:
            self.say(prompt)
        duration = phrase_time_limit or timeout
        print(f"Слушаю {duration} сек...")
        audio = self._record(duration)
        try:
            text = self.recognizer.recognize_google(audio, language=LANGUAGE)
            print(f"[Вы сказали]: {text}")
            return text.lower().strip()
        except sr.UnknownValueError:
            print("Не удалось распознать речь.")
            return ""
        except sr.RequestError as e:
            print(f"Ошибка сервиса распознавания: {e}")
            return ""
 
 
def contains_any(text: str, *keywords: str) -> bool:
    return any(k in text for k in keywords)
 
 
#  Управление браузером 
class BrowserController:
 
    def __init__(self):
        self.driver = None
 
    def is_open(self) -> bool:
        return self.driver is not None
 
    def open(self) -> str | None:
        if self.is_open():
            return None
        options = Options()
        options.binary_location = FIREFOX_BINARY
        service = Service(executable_path=GECKODRIVER_PATH)
        try:
            self.driver = webdriver.Firefox(options=options, service=service)
            self.driver.get(DEFAULT_URL)
            return None
        except Exception as e:
            self.driver = None
            return f"Не удалось открыть браузер: {e}"
 
    def close(self) -> None:
        if self.is_open():
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
 
    def goto(self, link: str) -> str:
        if not self.is_open():
            return "Браузер не открыт."
        if not link:
            return "Ссылка не распознана."
        link = link.replace(" ", "")
        if not link.startswith(("http://", "https://")):
            link = "https://" + link
        try:
            self.driver.get(link)
            return f"Перешли на {self.driver.current_url}"
        except Exception as e:
            return f"Не удалось открыть ссылку: {e}"
 
    def close_tab(self) -> bool:
        if not self.is_open():
            return False
        try:
            self.driver.close()
            if not self.driver.window_handles:
                self.driver = None
                return False
            self.driver.switch_to.window(self.driver.window_handles[0])
            return True
        except Exception:
            self.driver = None
            return False
 
    def fullscreen(self) -> None:
        if not self.is_open():
            return
        try:
            self.driver.fullscreen_window()
        except Exception:
            pass
 
    def refresh(self) -> None:
        if not self.is_open():
            return
        try:
            self.driver.refresh()
        except Exception:
            pass
 
    def whereami(self) -> str:
        if not self.is_open():
            return "Браузер не открыт."
        try:
            return f"Мы на странице {self.driver.title}"
        except Exception as e:
            return f"Не удалось получить информацию о странице: {e}"
 
 
BROWSER_HELP = (
    "Доступные команды браузера: перейти по ссылке, закрыть вкладку, "
    "выйти из браузера, во весь экран, обновить страницу, пауза, "
    "назад в меню, где я."
)
 
 
def browser_menu(browser: BrowserController, voice: Voice) -> None:
    error = browser.open()
    if error:
        voice.say(error)
        return
    voice.say("Браузер открыт. " + BROWSER_HELP)
 
    while True:
        command = voice.listen("Слушаю команду для браузера.")
 
        if not command:
            continue
 
        if contains_any(command, "перейти", "открой сайт", "открыть ссылку"):
            link = voice.listen("Назовите ссылку или адрес сайта.")
            voice.say(browser.goto(link))
 
        elif contains_any(command, "выйти из браузера", "закрой браузер", "закрыть браузер"):
            voice.say("Закрываю браузер.")
            browser.close()
            return
 
        elif contains_any(command, "закрой вкладку", "закрыть вкладку"):
            if not browser.close_tab():
                voice.say("Открытых вкладок больше нет, выходим из режима браузера.")
                return
            voice.say("Вкладка закрыта.")
 
        elif contains_any(command, "во весь экран", "разверни", "полный экран"):
            browser.fullscreen()
            voice.say("Окно развёрнуто на весь экран.")
 
        elif contains_any(command, "обнови страницу", "перезагрузи страницу"):
            browser.refresh()
            voice.say("Страница перезагружена.")
 
        elif contains_any(command, "пауза", "подожди"):
            voice.say("Пауза.")
            time.sleep(2)
 
        elif contains_any(command, "назад в меню", "главное меню", "вернуться"):
            voice.say("Возврат в главное меню, браузер остаётся открытым.")
            return
 
        elif contains_any(command, "где я"):
            voice.say(browser.whereami())
 
        elif contains_any(command, "помощь", "команды"):
            voice.say(BROWSER_HELP)
 
        else:
            voice.say("Не распознал команду, повторите.")
 
 
#  Системные функции 
 
def confirm(voice: Voice, prompt: str) -> bool:
    answer = voice.listen(prompt + " Скажите да или нет.")
    return contains_any(answer, "да", "подтверждаю", "точно")
 
 
def shutdown_pc(voice: Voice) -> None:
    if confirm(voice, "Вы точно хотите выключить компьютер?"):
        voice.say("Выключаю компьютер через пять секунд.")
        os.system("shutdown /s /t 5")
    else:
        voice.say("Отменено.")
 
 
def restart_pc(voice: Voice) -> None:
    if confirm(voice, "Вы точно хотите перезагрузить компьютер?"):
        voice.say("Перезагружаю компьютер через пять секунд.")
        os.system("shutdown /r /t 5")
    else:
        voice.say("Отменено.")
 
 
def lock_pc(voice: Voice) -> None:
    voice.say("Блокирую компьютер.")
    os.system("rundll32.exe user32.dll,LockWorkStation")
 
 
def open_program(voice: Voice) -> None:
    path = voice.listen("Назовите полный путь к программе.")
    if not path:
        voice.say("Путь не распознан.")
        return
    try:
        os.startfile(path)
        voice.say("Программа запущена.")
    except Exception as e:
        voice.say(f"Не удалось запустить программу: {e}")
 
 
def open_notepad(voice: Voice) -> None:
    try:
        os.startfile("notepad.exe")
        voice.say("Блокнот открыт.")
    except Exception as e:
        voice.say(f"Не удалось открыть Блокнот: {e}")
 
 
def show_system_info(voice: Voice) -> None:
    info = [f"Операционная система: {os.name}"]
    try:
        info.append(f"Имя пользователя: {os.getlogin()}")
    except Exception:
        pass
    info.append(f"Текущая рабочая папка: {os.getcwd()}")
    text = ". ".join(info)
    print(text)
    voice.say(text)
 
 
def open_folder(voice: Voice) -> None:
    folder = voice.listen("Назовите путь к папке.")
    if not folder:
        voice.say("Путь не распознан.")
        return
    try:
        os.startfile(folder)
        voice.say("Папка открыта.")
    except Exception as e:
        voice.say(f"Не удалось открыть папку: {e}")
 
 
#  Главное меню 
 
MAIN_HELP = (
    "Доступные команды: открой браузер, выключи компьютер, перезагрузи компьютер, "
    "заблокируй компьютер, открой программу, открой блокнот, информация о системе, "
    "открой папку, выход."
)
 
 
def main() -> None:
    voice = Voice()
    voice.say("Здравствуйте, это голосовой центр управления компьютером. " + MAIN_HELP)
 
    browser = BrowserController()
 
    while True:
        try:
            command = voice.listen("Слушаю команду.")
        except KeyboardInterrupt:
            break
 
        if not command:
            continue
 
        if contains_any(command, "открой браузер", "браузер"):
            browser_menu(browser, voice)
 
        elif contains_any(command, "выключи компьютер", "выключить компьютер"):
            shutdown_pc(voice)
 
        elif contains_any(command, "перезагрузи компьютер", "перезагрузить компьютер"):
            restart_pc(voice)
 
        elif contains_any(command, "заблокируй компьютер", "заблокировать компьютер"):
            lock_pc(voice)
 
        elif contains_any(command, "открой программу", "запусти программу"):
            open_program(voice)
 
        elif contains_any(command, "открой блокнот", "блокнот"):
            open_notepad(voice)
 
        elif contains_any(command, "информация о системе", "системная информация"):
            show_system_info(voice)
 
        elif contains_any(command, "открой папку", "открыть папку"):
            open_folder(voice)
 
        elif contains_any(command, "помощь", "команды", "что ты умеешь"):
            voice.say(MAIN_HELP)
 
        elif contains_any(command, "выход", "закончить", "завершить работу"):
            if browser.is_open():
                browser.close()
            voice.say("До свидания!")
            break
 
        else:
            voice.say("Не распознал команду, повторите.")
 
 
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Завершение работы по Ctrl+C.")
