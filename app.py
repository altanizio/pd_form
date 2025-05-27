import streamlit as st
import pandas as pd
import numpy as np
import io

dados = pd.read_excel(
    "experimento_nao_rotulado_rev01.xlsx", sheet_name="Codificação", skiprows=1
)
variaveis = dados.columns[1:6]
variaveis_A = list(variaveis + "_A")
variaveis_B = list(variaveis + "_B")
variaveis = variaveis_A + variaveis_B
colunas = list(dados.columns)
colunas[1:] = variaveis
dados.columns = colunas

niveis = pd.read_excel("experimento_nao_rotulado_rev01.xlsx", sheet_name="Níveis")
niveis["Variável"] = niveis["Variável"].ffill()

custo = pd.read_excel("experimento_nao_rotulado_rev01.xlsx", sheet_name="Custo")
tempo = pd.read_excel("experimento_nao_rotulado_rev01.xlsx", sheet_name="Tempo")


st.title("Formulário para Pesquisa de Preferência Declarada")

nome = st.text_input("Nome da empresa (*)", key="nome")

st.header(
    "Em relação ao principal produto expedido pela empresa (o com maior movimentação anual em peso), responda as seguintes questões:"
)

produto = st.text_input("1. Qual o produto? (*)", key="produto")

modos_utilizados = st.multiselect(
    "2. Qual o modo de transporte utilizado? Se multimodal, marcar mais de um. (*)",
    [
        "Rodoviário",
        "Ferroviário",
        "Portuário",
        "Hidroviário",
        "Aeroviário",
        "Dutoviário",
        "Outro",
    ],
    key="modos_utilizados",
)

modo_outro = ""
if "Outro" in modos_utilizados:
    modo_outro = st.text_input("Qual outro modo?", key="modo_outro")

motivo_uso = st.text_area("3. Por que você utiliza esse modo? (*)", key="motivo_uso")

modos_nao_usaria = st.multiselect(
    "4. Existe algum modo que você **não usaria** para fazer o transporte desse produto, independentemente de tempo, custo, confiabilidade, flexibilidade e segurança? Se sim, por quê?",
    [
        "Rodoviário",
        "Ferroviário",
        "Portuário",
        "Hidroviário",
        "Aeroviário",
        "Dutoviário",
        "Outro",
    ],
    key="modos_nao_usaria",
)

nao_usaria_outro = ""
if "Outro" in modos_nao_usaria:
    nao_usaria_outro = st.text_input(
        "Qual outro modo você não usaria?", key="nao_usaria_outro"
    )

motivo_nao_usaria = st.text_area(
    "Por que você não usaria esse(s) modo(s)?", key="motivo_nao_usaria"
)

custo_atual = st.selectbox(
    "5. Qual a faixa de custo de transporte? (*)",
    [
        "Até R$ 50 por tonelada",
        "Entre R$ 50 e R$ 100 por tonelada",
        "Entre R$ 100 e R$ 250 por tonelada",
        "Entre R$ 250 e R$ 500 por tonelada",
        "Entre R$ 500 e R$ 1000 por tonelada",
        "Acima de R$ 1000 por tonelada",
    ],
    key="custo_atual",
)

distancia = st.selectbox(
    "6. Qual a faixa de distância de transporte em quilômetros? (*)",
    ["Até 100", "100–300", "300–500", "500–1000", "Acima de 1000"],
    key="distancia",
)

st.markdown("**Campos com (*) são obrigatórios.**")

conjuntos = []
with open("conjuntos.txt", "r", encoding="utf-8") as f:
    for linha in f:
        partes = linha.strip().split(",")
        conjuntos.append([int(p) for p in partes])

batch_escolha = st.radio("Qual conjunto de cartões?", options=conjuntos, key="batch")

custo_i = (
    custo.loc[custo["Nível do formulário"] == custo_atual]
    .melt(id_vars="Nível do formulário", value_name="Ajuste", var_name="Nível")
    .loc[1:2, ["Nível", "Ajuste"]]
)
custo_i_map = dict(zip(custo_i["Nível"], custo_i["Ajuste"]))

tempo_i = (
    tempo.loc[tempo["Distância (km)"] == distancia]
    .melt(id_vars="Distância (km)", value_name="Ajuste", var_name="Nível")
    .loc[:, ["Nível", "Ajuste"]]
)
tempo_i_map = dict(zip(tempo_i["Nível"], tempo_i["Ajuste"]))

map_valores = custo_i_map | tempo_i_map


campos_ok = all(
    [
        st.session_state.get("nome", "").strip() != "",
        st.session_state.get("produto", "").strip() != "",
        st.session_state.get("modos_utilizados", []) != [],
        st.session_state.get("motivo_uso", "").strip() != "",
        st.session_state.get("custo_atual", "").strip() != "",
        st.session_state.get("distancia", "").strip() != "",
    ]
)


if "cartao_atual" not in st.session_state:
    st.session_state.cartao_atual = 0

if "respostas" not in st.session_state:
    st.session_state.respostas = {}

i = st.session_state.cartao_atual

if "iniciado" not in st.session_state:
    st.session_state.iniciado = False

if not st.session_state.iniciado:
    if st.button("Iniciar experimento", type="secondary", use_container_width=True):
        if not campos_ok:
            st.warning(
                "Preencha todas as perguntas obrigatórias antes de iniciar o experimento."
            )
            st.session_state.iniciado = False
        else:
            st.session_state.iniciado = True
            st.rerun()

if st.session_state.iniciado:
    if "cartoes_embaralhados" not in st.session_state:
        st.session_state.cartoes_embaralhados = np.random.permutation(batch_escolha)
    cartoes = st.session_state.cartoes_embaralhados
    if i < len(cartoes):
        cartao = cartoes[i]
        st.markdown(f"## Cartão {cartao}")

        option_i_data = dados.loc[dados["Cartão"] == cartao].melt(
            id_vars="Cartão", value_name="Código", var_name="Variável"
        )
        option_i_data["option"] = option_i_data["Variável"].apply(lambda x: x[-1])
        option_i_data["Variável"] = option_i_data["Variável"].apply(lambda x: x[:-2])
        option_i_data = option_i_data.merge(niveis, how="left")
        option_i_data["Nível"] = (
            option_i_data["Nível"].map(map_valores).fillna(option_i_data["Nível"])
        )

        def formatar_nivel(row):
            if row["Variável"] == "Custo":
                return f"R$ {row['Nível']}/tonelada"
            return row["Nível"]

        option_i_data["Nível"] = option_i_data.apply(formatar_nivel, axis=1)
        df_pivot = option_i_data.pivot(
            index="Variável", columns="option", values="Nível"
        )

        ordem_var = ["Custo", "Tempo", "Confiabilidade", "Flexibilidade", "Segurança"]
        df_pivot.index = pd.CategoricalIndex(
            df_pivot.index, categories=ordem_var, ordered=True
        )
        df_pivot = df_pivot.sort_index()

        col1, col2 = st.columns(2)

        with col1:
            conteudo_a = "<div style='border: 2px solid #D3D3D3; border-radius: 10px; padding: 15px;'>"
            conteudo_a += "<h4 style='margin-top: 0;'>Opção A</h4>"
            for idx, val in df_pivot["A"].items():
                conteudo_a += f"<p><strong>{idx}:</strong> {val}</p>"
            conteudo_a += "</div>"
            st.markdown(conteudo_a, unsafe_allow_html=True)

        with col2:
            conteudo_b = "<div style='border: 2px solid #D3D3D3; border-radius: 10px; padding: 15px;'>"
            conteudo_b += "<h4 style='margin-top: 0;'>Opção B</h4>"
            for idx, val in df_pivot["B"].items():
                conteudo_b += f"<p><strong>{idx}:</strong> {val}</p>"
            conteudo_b += "</div>"
            st.markdown(conteudo_b, unsafe_allow_html=True)

        opcoes = ["Selecione uma opção", "A", "B"]

        escolha = st.radio(
            "Qual opção você prefere?", options=opcoes, key=f"cartao_{cartao}"
        )

        if escolha != "Selecione uma opção":
            st.write(f"Você escolheu: {escolha}")
            if st.button("Próximo", type="secondary", use_container_width=True):
                st.session_state.respostas[cartao] = escolha
                st.session_state.cartao_atual += 1
                st.rerun()
        else:
            st.write("Por favor, selecione uma opção.")

    else:
        df_resultado = (
            pd.DataFrame.from_dict(
                st.session_state.respostas, orient="index", columns=["Escolha"]
            )
            .reset_index()
            .rename(columns={"index": "Cartão"})
        )

        df_resultado.insert(0, "Nome", nome)
        df_resultado.insert(1, "Produto Principal", produto)
        df_resultado.insert(2, "Modos Utilizados", ", ".join(modos_utilizados))
        df_resultado.insert(3, "Outro Modo (se houver)", modo_outro)
        df_resultado.insert(4, "Motivo Uso do Modo", motivo_uso)
        df_resultado.insert(5, "Modos Não Usaria", ", ".join(modos_nao_usaria))
        df_resultado.insert(6, "Outro Modo Não Usaria", nao_usaria_outro)
        df_resultado.insert(7, "Motivo Não Usaria", motivo_nao_usaria)
        df_resultado.insert(8, "Custo Atual", custo_atual)
        df_resultado.insert(9, "Distância", distancia)
        df_resultado.insert(10, "Conjunto de Cartões", str(batch_escolha))

        st.dataframe(df_resultado)

        st.success(
            "Você completou todos os cartões! Baixe os resultados no botão abaixo."
        )

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_resultado.to_excel(writer, sheet_name="Respostas", index=False)

        st.download_button(
            label="📥 Baixar respostas em Excel",
            data=buffer.getvalue(),
            file_name=f"respostas_{nome.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
            use_container_width=True,
        )

        idx_atual = conjuntos.index(st.session_state["batch"])
        proximo_idx = (idx_atual + 1) % len(conjuntos)

        if st.button("Nova pesquisa", type="primary", use_container_width=True):
            st.session_state.clear()

            st.session_state["batch"] = conjuntos[proximo_idx]

            st.session_state["nome"] = ""
            st.session_state["produto"] = ""
            st.session_state["modos_utilizados"] = []
            st.session_state["modo_outro"] = ""
            st.session_state["motivo_uso"] = ""
            st.session_state["modos_nao_usaria"] = []
            st.session_state["nao_usaria_outro"] = ""
            st.session_state["motivo_nao_usaria"] = ""
            st.session_state["custo_atual"] = "Até R$ 50 por tonelada"
            st.session_state["distancia"] = "Até 100"

            st.rerun()


st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; font-size: 0.9rem; color: gray;">
       Formulário para Pesquisa de Preferência Declarada - Consórcio Concremat/Transplan<br>
        <span style="font-size: 0.8rem;">Versão 1.0.0</span>
    </div>
    """,
    unsafe_allow_html=True,
)
