# Registro de verificação — Orenu → site

**Última verificação:** 2026-08-11

Cada linha abaixo é uma execução do sync Orenu → site. É gerada por
`scripts/write_sync_ledger.py`, a partir do relatório dos próprios scripts de
sync — **não editar à mão** (o gerador aborta se o formato da tabela mudar).

## O que uma linha afirma

Que, na data indicada, o sync comparou N linhas do Orenu contra os arquivos MDX
deste site e encontrou K divergências (drift, stubs, órfãos, atualizações de
campo). Isso exercita as pernas **1, 2 e 4** do gate obrigatório de
não-contradição da [ADR-024][adr] / `docs/personal-sites-integration-contract.md`
§4: títulos, empregadores e datas · prêmios, credenciais e reconhecimentos · e a
regra de que nenhum fato do site existe sem linha no Orenu.

## O que uma linha NÃO afirma

A perna **3** do §4 — a regra de OPSEC sobre afirmação quantitativa de
imigração em texto público e em mensagem de commit — **não é verificada aqui**.
Nada no sync lê prosa. O silêncio desta tabela sobre isso é deliberado: não
tratar como cobertura.

## Por que este arquivo existe

O sync é *zero-churn*: quando tudo é no-op, não há mudança de arquivo e não há
PR. Num repositório cujo único escritor recorrente é esse workflow, zero-churn
garante zero commits — e o GitHub desativa workflow agendado após 60 dias de
inatividade do **repositório**. Ou seja, o critério de sucesso do mecanismo é o
que o mata, e isso já aconteceu uma vez, em 2026-08-09.

Manter o repositório vivo, porém, é **efeito colateral**, não a razão. A razão é
que o gate do §4 é obrigatório e não havia nenhuma evidência de quando ele fora
exercido pela última vez. O que seria commit de ruído vira trilha de auditoria
do invariante.

## Como ler o resultado

| símbolo | significa |
|---|---|
| ✅ | comparou e não achou divergência |
| ⚠️ | comparou e achou divergência — há PR aberto para revisar |
| ⛔ | **não conseguiu apurar** — a execução falhou ou o relatório não foi lido |

⛔ nunca deve ser lido como "está tudo bem". `0` significa *conferido, nada
encontrado*; `?` significa *não deu para saber*. O gerador é escrito para nunca
colapsar os dois.

[adr]: https://github.com/VitorMRodovalho/rodovalho-finance/blob/main/decisions/ADR-024-orenu-as-source-of-truth-personal-branding-sites.md

---

| Data (UTC) | Fontes conferidas | Divergências | Resultado | Execução |
|---|---|---|---|---|
| 2026-08-11 | **11** (credentials 3 · awards 3 · community 5) | **0** | ✅ sem divergência | [log](https://github.com/VitorMRodovalho/vitormr-site/actions/runs/31466874517) |
| 2026-08-10 | **11** (credentials 3 · awards 3 · community 5) | **0** | ✅ sem divergência | [log](https://github.com/VitorMRodovalho/vitormr-site/actions/runs/31365270310) |
