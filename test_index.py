import base64
import os
import pytest
from unittest.mock import patch, MagicMock
import index


def test_variaveis_ambiente_carregadas():
    assert index.SMTP_SERVER == "smtp.gmail.com"
    assert index.SMTP_PORT == 587

def test_salvar_pdf_base64(tmp_path):
    dados_mock_base64 = "data:application/pdf;base64,UERGLUZBTFNP"
    caminho_teste = os.path.join(tmp_path, "boleto_teste.pdf")

    with patch("index.CAMINHO_PDF", caminho_teste), patch(
        "index.PASTA_BOLETOS", tmp_path
    ):
        index.salvar_pdf(dados_mock_base64, MagicMock())

    assert os.path.exists(caminho_teste)
    with open(caminho_teste, "r") as f:
        assert f.read() == "PDF-FALSO"