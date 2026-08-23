import base64
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

SITE_BOLETO = os.getenv("SITE_BOLETO", "")
EMAIL_USER = os.getenv("EMAIL_USER", "")
PASSWORD_USER = os.getenv("PASSWORD_USER", "")
EMAIL_DE_ENVIO = os.getenv("EMAIL_DE_ENVIO", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").strip().replace(" ", "")

PASTA_BOLETOS = os.path.abspath("boletos")
NOME_ARQUIVO_PDF = "Boleto_Atual.pdf"
CAMINHO_PDF = os.path.join(PASTA_BOLETOS, NOME_ARQUIVO_PDF)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def inicializar_navegador() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    navegador = webdriver.Chrome(options=options)
    navegador.set_window_size(1920, 1080)
    return navegador


def realizar_login(navegador: webdriver.Chrome, wait: WebDriverWait) -> None:
    navegador.get(SITE_BOLETO)

    campo_login = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='text']"))
    )
    campo_login.clear()
    campo_login.send_keys(EMAIL_USER)

    campo_senha = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='password']"))
    )
    campo_senha.clear()
    campo_senha.send_keys(PASSWORD_USER)

    botao_entrar = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Entrar')]"))
    )
    botao_entrar.click()


def extrair_url_pdf(navegador: webdriver.Chrome, wait: WebDriverWait) -> str:
    drop = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(@class, 'js-dropdown__current')]")
        )
    )
    navegador.execute_script("arguments[0].click();", drop)

    btn = wait.until(
        EC.presence_of_element_located((By.ID, "btn_imprimir_fat_home_"))
    )
    navegador.execute_script("arguments[0].click();", btn)

    xpath_pdf = (
        "//*[@id='modalImpressao']//iframe | "
        "//*[@id='modalImpressao']//embed | "
        "//*[@id='modalImpressao']//object"
    )
    elemento_pdf = wait.until(EC.presence_of_element_located((By.XPATH, xpath_pdf)))

    url_pdf = elemento_pdf.get_attribute("src") or elemento_pdf.get_attribute("data")
    if not url_pdf:
        raise ValueError("Não foi possível capturar a URL/Data do PDF.")

    return url_pdf


def salvar_pdf(url_pdf: str, navegador: webdriver.Chrome) -> None:
    os.makedirs(PASTA_BOLETOS, exist_ok=True)

    if url_pdf.startswith("data:application/pdf;base64,"):
        dados_base64 = url_pdf.split(",")[1]
        conteudo_pdf = base64.b64decode(dados_base64)
    else:
        session = requests.Session()
        for cookie in navegador.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])
        resposta = session.get(url_pdf)
        resposta.raise_for_status()
        conteudo_pdf = resposta.content

    with open(CAMINHO_PDF, "wb") as arquivo:
        arquivo.write(conteudo_pdf)


def enviar_email(caminho_anexo: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Boleto do Mês"
    msg["From"] = EMAIL_DE_ENVIO
    msg["To"] = EMAIL_USER
    msg.set_content("Oi mãe! Segue em anexo o boleto deste mês.")

    with open(caminho_anexo, "rb") as arquivo:
        conteudo_pdf = arquivo.read()
        msg.add_attachment(
            conteudo_pdf,
            maintype="application",
            subtype="pdf",
            filename="Boleto_Mes.pdf",
        )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_DE_ENVIO, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)


def main() -> None:
    navegador = inicializar_navegador()
    wait = WebDriverWait(navegador, 20)

    try:
        realizar_login(navegador, wait)
        url_pdf = extrair_url_pdf(navegador, wait)
        salvar_pdf(url_pdf, navegador)
        enviar_email(CAMINHO_PDF)
        print("Processo concluído com sucesso!")
    except Exception as erro:
        print(f"Ocorreu um erro durante a execução: {erro}")
    finally:
        navegador.quit()


if __name__ == "__main__":
    main()