import math
import tempfile
import unittest
import zipfile
from pathlib import Path

import fitz
from openpyxl import load_workbook
from pptx import Presentation

import gerar_entrega as ge


def _textos(slide):
    return " ".join(f.text_frame.text for f in slide.shapes if f.has_text_frame) + " " + " ".join(
        c.text for f in slide.shapes if f.has_table for linha in f.table.rows for c in linha.cells)


class TestArtefatos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.saidas = ge.gerar(cls.tmp.name)
        cls.dados = ge.carregar()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pptx_editavel_com_capa_notas_e_retorno(self):
        prs = Presentation(self.saidas["Apresentacao_T2.pptx"])
        slides = list(prs.slides)
        self.assertEqual(len(slides), len(ge.roteiro(self.dados)))
        for nome in ge.INTEGRANTES:
            self.assertIn(nome, _textos(slides[0]))
        for s in slides:
            self.assertTrue(s.notes_slide.notes_text_frame.text.strip())
            self.assertFalse([f for f in s.shapes if f._element.tag.endswith("}pic")], "sem imagens/screenshots")
        rede = slides[2]
        self.assertIn("retorno", _textos(rede))
        self.assertIn("tailEnd", "".join(f._element.xml for f in rede.shapes))
        q2 = ge.principal(self.dados["inicial"])["indices"]["Q2"]
        todo = " ".join(_textos(s) for s in slides)
        self.assertIn(ge.br(q2["R"], 4), todo)
        self.assertIn(ge.br(q2["perdas"], 0), todo)
        self.assertIn("G/G/2/8", _textos(slides[8]))

    def test_xlsx_formulas_e_dados_brutos(self):
        wb = load_workbook(self.saidas["Indices_T2.xlsx"])
        self.assertTrue({"Leia-me", "Estados_inicial", "Estados_melhorado", "Indices", "Comparacao",
                         "Replicacoes"} <= set(wb.sheetnames))
        for cen in ge.CENARIOS:
            ws, rep = wb[f"Estados_{cen}"], ge.principal(self.dados[cen])
            self.assertAlmostEqual(ws["B2"].value, rep["global_time"])
            tempos = {}
            for linha in ws.iter_rows(min_row=6, values_only=True):
                tempos.setdefault(linha[0], []).append(linha[6])
                self.assertTrue(all(str(v).startswith("=") for v in linha[7:10]))
            for fila in ge.FILAS:
                esperado = rep["queues"][fila]["accumulated"]
                self.assertEqual(len(tempos[fila]), len(esperado), fila)
                for n, (lido, ref) in enumerate(zip(tempos[fila], esperado)):
                    # XLSX serializa ~15-17 dígitos; tolerância só absorve o último ulp.
                    self.assertTrue(math.isclose(lido, ref, rel_tol=1e-12, abs_tol=1e-10), (fila, n, lido, ref))
        ind = wb["Indices"]
        for linha in ind.iter_rows(min_row=2, values_only=True):
            self.assertTrue(all(str(v).startswith("=") for v in linha[2:]), linha)

    def test_roteiro_pdf_e_md(self):
        with fitz.open(self.saidas["Roteiro_T2.pdf"]) as doc:
            texto = "".join(p.get_text() for p in doc)
        md = self.saidas["Roteiro_T2.md"].read_text(encoding="utf-8")
        n = len(ge.roteiro(self.dados))
        for alvo in (texto, md):
            for nome in ge.INTEGRANTES:
                self.assertIn(nome, alvo)
            self.assertIn(f"Slide {n}", alvo)
            self.assertIn("YouTube", alvo)
        self.assertTrue(self.saidas["VIDEO_PENDENTE.txt"].is_file())


class TestEmpacotar(unittest.TestCase):
    def test_exige_pdf_exclui_lixo_e_inclui_motor(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for rel in ("T2/analise.py", "T2/resultados/inicial.json", "T2/__pycache__/x.pyc",
                        "T2/.workflow/estado.md", "T2/logs/a.log", "T2/entrega/~$Apresentacao_T2.pptx",
                        "T1/simulador_fila.py", "T1/outro.py"):
                (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
                (raiz / rel).write_text("x", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                ge.empacotar(raiz)
            (raiz / "T2/entrega/Apresentacao_T2.pdf").write_bytes(b"%PDF")
            ge.empacotar(raiz)
            with zipfile.ZipFile(ge.empacotar(raiz)) as z:  # 2ª vez: não inclui o próprio ZIP
                nomes = set(z.namelist())
        self.assertEqual(nomes, {"T2/analise.py", "T2/resultados/inicial.json",
                                 "T2/entrega/Apresentacao_T2.pdf", "T1/simulador_fila.py"})


if __name__ == "__main__":
    unittest.main()
