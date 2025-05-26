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


st.title("Formulário de Preferência Declarada")
st.header("Informações do Participante")

nome = st.text_input("Nome completo do entrevistado")

custo_atual = st.selectbox(
    "Custo atual de transporte (R$ por tonelada):",
    [
        "Até R$ 50 por tonelada",
        "Entre R$ 50 e R$ 100 por tonelada",
        "Entre R$ 100 e R$ 250 por tonelada",
        "Entre R$ 250 e R$ 500 por tonelada",
        "Entre R$ 500 e R$ 1000 por tonelada",
        "Acima de R$ 1000 por tonelada",
    ],
)
distancia = st.selectbox(
    "Distância média percorrida pela carga (km):",
    ["Até 100", "100–300", "300–500", "500–1000", "Acima de 1000"],
)

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


if "cartao_atual" not in st.session_state:
    st.session_state.cartao_atual = 0

if "respostas" not in st.session_state:
    st.session_state.respostas = {}

i = st.session_state.cartao_atual

if "iniciado" not in st.session_state:
    st.session_state.iniciado = False

if not st.session_state.iniciado:
    if st.button("Iniciar experimento"):
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

        escolha = st.radio(
            "Qual opção você prefere?", options=["A", "B"], key=f"cartao_{cartao}"
        )

        if st.button("Próximo"):
            st.session_state.respostas[cartao] = escolha
            st.session_state.cartao_atual += 1
            st.rerun()

    else:
        st.success("Você completou todos os cartões!")

        df_resultado = (
            pd.DataFrame.from_dict(
                st.session_state.respostas, orient="index", columns=["Escolha"]
            )
            .reset_index()
            .rename(columns={"index": "Cartão"})
        )

        df_resultado.insert(0, "Nome", nome)
        df_resultado.insert(1, "Custo Atual", custo_atual)
        df_resultado.insert(2, "Distância", distancia)
        df_resultado.insert(3, "Conjunto de Cartões", str(batch_escolha))

        st.dataframe(df_resultado)

        if st.button("Salvar respostas"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_resultado.to_excel(writer, sheet_name="Respostas", index=False)

            st.success("Respostas salvas com sucesso!")

            # Botão para o usuário baixar o Excel
            st.download_button(
                label="📥 Baixar respostas em Excel",
                data=buffer.getvalue(),
                file_name=f"respostas_{nome.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        if st.button("Nova pesquisa"):
            st.session_state.clear()
            st.rerun()
