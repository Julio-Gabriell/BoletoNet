import os
import time
import glob
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

SITE_BOLETO = os.getenv("SITE_BOLETO")
EMAIL_USER = os.getenv("EMAIL_USER")
PASSWORD_USER = os.getenv("PASSWORD_USER")
EMAIL_DE_ENVIO = os.getenv("EMAIL_DE_ENVIO")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
PASTA_BOLETOS = os.path.abspath("boletos")
DIRETORIO_BOLETOS = PASTA_BOLETOS
CAMINHO_PDF = os.path.join(PASTA_BOLETOS, "Boleto_Atual.pdf")


def inicializar_navegador() -> webdriver.Chrome:
    os.makedirs(PASTA_BOLETOS, exist_ok=True)

    options = Options()

    if os.getenv("CI"):
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    prefs = {
        "download.default_directory": PASTA_BOLETOS,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)

    navegador = webdriver.Chrome(options=options)

    if os.getenv("CI"):
        navegador.set_window_size(1920, 1080)
    else:
        navegador.set_window_size(375, 812)

    return navegador


def realizar_login(navegador: webdriver.Chrome, wait: WebDriverWait) -> None:
    navegador.get(SITE_BOLETO)

    campo_login = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='text']"))
    )
    navegador.execute_script("arguments[0].value = arguments[1];", campo_login, EMAIL_USER)
    navegador.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", campo_login)

    campo_senha = navegador.find_element(By.XPATH, "//input[@type='password']")
    navegador.execute_script("arguments[0].value = arguments[1];", campo_senha, PASSWORD_USER)
    navegador.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", campo_senha)

    botao_entrar = navegador.find_element(By.XPATH, "//*[contains(text(), 'Entrar')]")
    navegador.execute_script("arguments[0].click();", botao_entrar)


def extrair_url_pdf(navegador: webdriver.Chrome, wait: WebDriverWait) -> str:
    xpath_selector = (
        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'baixar') "
        "or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'pdf')]"
    )

    botao_download = wait.until(
        EC.element_to_be_clickable((By.XPATH, xpath_selector))
    )
    navegador.execute_script("arguments[0].click();", botao_download)

    for _ in range(15):
        time.sleep(1)
        arquivos = glob.glob(os.path.join(PASTA_BOLETOS, "*.pdf"))
        if arquivos:
            break

    if not arquivos:
        raise FileNotFoundError("O arquivo PDF do boleto nao foi baixado.")

    arquivo_baixado = max(arquivos, key=os.path.getctime)
    if os.path.exists(CAMINHO_PDF):
        os.remove(CAMINHO_PDF)
    os.rename(arquivo_baixado, CAMINHO_PDF)
    return CAMINHO_PDF

def salvar_pdf(dados_pdf: str, navegador: webdriver.Chrome) -> None:
    if dados_pdf.startswith("data:application/pdf;base64,"):
        dados_pdf = dados_pdf.split(",")[1]

    conteudo_pdf = base64.b64decode(dados_pdf)

    os.makedirs(PASTA_BOLETOS, exist_ok=True)
    with open(CAMINHO_PDF, "wb") as f:
        f.write(conteudo_pdf)

def enviar_email(caminho_anexo: str) -> None:
    msg = MIMEMultipart()
    msg['From'] = EMAIL_DE_ENVIO
    msg['To'] = EMAIL_DE_ENVIO
    msg['Subject'] = "Boleto do Mês Disponível"

    corpo = "Olá,\n\nSegue em anexo o boleto deste mês gerado automaticamente.\n\nAtenciosamente."
    msg.attach(MIMEText(corpo, 'plain'))

    with open(caminho_anexo, "rb") as f:
        anexo = MIMEApplication(f.read(), _subtype="pdf")
        anexo.add_header('Content-Disposition', 'attachment', filename=os.path.basename(caminho_anexo))
        msg.attach(anexo)

    with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
        server.login(EMAIL_DE_ENVIO, EMAIL_APP_PASSWORD)
        server.send_message(msg)


def main() -> None:
    navegador = inicializar_navegador()
    wait = WebDriverWait(navegador, 20)

    try:
        realizar_login(navegador, wait)
        extrair_url_pdf(navegador, wait)
        enviar_email(CAMINHO_PDF)
        print("Processo concluido com sucesso!")
    except Exception as erro:
        print(f"Ocorreu um erro na etapa: {erro}")
        raise erro
    finally:
        navegador.quit()


if __name__ == "__main__":
    main()