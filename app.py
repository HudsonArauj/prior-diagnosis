import streamlit as st
from llama_parse import LlamaParse
from utils import formated_docs, chain_structured_invoke, chain_diagnostico, convert_to_float, convert_to_int
from PyPDF2 import PdfReader
import os
import pandas as pd
from streamlit import session_state as ss
from utils import *

import plotly.express as px
import plotly.graph_objects as go



st.markdown(
    """
    ## Diagnóstico prévio.
    """,
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader("Gerar diagnóstico do exame.", type=['pdf'])

if uploaded_file:
    file_path = os.path.join('.', uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    parser = LlamaParse(
        result_type="markdown" 
    )

    try:
        parsing_result = parser.load_data([file_path])
    except Exception as e:
        st.error(f"Erro ao analisar o arquivo: {e}")
        parsing_result = []

    button_gerar_diagnostico = st.button(
        label='Diagnóstico',
        type='primary'
    )
    
    
    if button_gerar_diagnostico:
        if not parsing_result:
            st.markdown('Por favor, insira um arquivo PDF válido para continuar.')
        else:
            with st.spinner('Gerando diagnóstico...'):
                
                data = chain_structured_invoke(formated_docs(parsing_result))
                data_dict = data.tool_calls[0]['args']
                # replace ',' to '.' for float conversion
                data_dict = {k: v.replace(",", ".") for k, v in data_dict.items()}
                st.title("Resultado do Exame de Sangue")
                st.write("## Dados do Paciente")
                st.write(f"**Idade:** {data_dict['idade']}")
                st.write(f"**Sexo:** {data_dict['sexo']}")
                st.write(f"**Data do exame:** {data_dict['data']}")

                st.write("## Resultados do Hemograma")
                
                #transformando o dicionário em um dataframe
                cwdf = pd.DataFrame(data_dict.items(), columns=['Dados extraídos', 'Resultado'])
                
                plaquetas = convert_to_float(data_dict.get('plaquetas', '0'))
                hemoglobina = convert_to_float(data_dict.get('hemoglobina', '0'))
                neutrofilos = convert_to_float(data_dict.get('neutrofilos', '0'))
                linfocitos = convert_to_float(data_dict.get('linfocitos', '0'))
                vcm = convert_to_float(data_dict.get('vcm', '0'))
                vmc = convert_to_float(data_dict.get('vmc', '0'))
                vpm = convert_to_float(data_dict.get('vpm', '0'))
                macroplaquetas = data_dict.get('macroplaquetas', 'False')
                medicacao = data_dict.get('medicacao', 'False')
                infeccao = data_dict.get('infeccao', 'False')
                idade = convert_to_int(data_dict.get('idade', '0'))
                leucocitos = convert_to_float(data_dict.get('leucocitos', '0'))
                chcm = convert_to_float(data_dict.get('chcm', '0')) 
               
                            
                result_diagnostico = chain_diagnostico(plaquetas, hemoglobina, neutrofilos, linfocitos, vcm, vmc, vpm, macroplaquetas, medicacao, infeccao, idade, sexo=data_dict['sexo'], data=data_dict['data'], leucocitos=leucocitos, chcm=chcm)

                
                
                if not cwdf.empty:
                    # Criar a tabela usando Plotly
                    fig = go.Figure(
                        data=[go.Table(
                            columnorder=[1, 2], 
                            columnwidth=[15, 40],
                            header = dict(
                                values = list(cwdf.columns),
                                font=dict(size=11, color = 'white'),
                                fill_color = '#264653',
                                line_color = 'darkslategray',
                                align = ['left','center'],
                                #text wrapping
                                height=20
                            ),
                            cells=dict(
                                values=[cwdf[col][3:].tolist() for col in cwdf.columns],
                                font=dict(size=12, color='black'),
                                align = ['left','center'],
                                fill_color='white',
                                height=20
                            )
                        )]
                    )
                    
                    fig.update_layout(
                        title_text="Resultado",
                        title_font_color='#264653',
                        title_x=0,
                        margin=dict(l=0, r=10, b=10, t=30),
                        height=480
                    )
                    
                    # Exibir a tabela no Streamlit
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.title('Diagnóstico:')
                    st.markdown(f"**Diagnóstico:** {result_diagnostico}")


                else:
                    st.write("Nenhum dado encontrado para exibir.")
                
                st.write("## Observações")
                st.write("Os resultados do exame devem ser analisados por um médico especializado para um diagnóstico preciso.")
    
    # Optionally, clean up the file after processing
    os.remove(file_path)