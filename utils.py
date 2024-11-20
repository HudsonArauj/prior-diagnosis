# bring in our LLAMA_CLOUD_API_KEY
from dotenv import load_dotenv
# bring in deps
import nest_asyncio
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from tqdm import tqdm
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
import os
from langchain_core.output_parsers import StrOutputParser
from langchain_pinecone import PineconeVectorStore


nest_asyncio.apply()

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

"""

Relevant Chains and functions

"""
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="pf-nlp", embedding=embeddings)


llm = ChatOpenAI(
    model="gpt-4o-2024-08-06",  # 100% json output
    temperature=0,
)


class GetSchema(BaseModel):
    class Config:
        arbitrary_types_allowed = True
    """Extrai valores relevantes de um documento de exame médico de hemograma"""
    idade: str = Field(description="Valor numérico de idade")
    sexo: str = Field(description="Valor de sexo")
    data: str = Field(description="Data do exame")

    hemacias: str = Field(description="Valor numérico de hemácias")
    hemoglobina: str = Field(description="Valor numérico de hemoglobina")
    hematocrito: str = Field(description="Valor numérico de hematocrito")
    vcm: str = Field(description="Valor numérico de VCM")
    hcm: str = Field(description="Valor numérico de HCM")
    chcm: str = Field(description="Valor numérico de CHCM")
    rdw: str = Field(description="Valor numérico de RDW")
    plaquetas: str = Field(
        description="Valor numérico de plaquetas em µL", examples=["10000"])
    vmp: str = Field(description="Valor numérico de VMP")
    vmc: str = Field(description="Valor numérico de VMC")
    vpm: str = Field(description="Valor numérico de VPM")
    macroplaquetas: str = Field(description="Valor booleano de macroplaquetas")
    medicacao: str = Field(description="Valor booleano de medicamento")
    infeccao: str = Field(description="Valor booleano de infecção")

    leucocitos: str = Field(
        description="Valor numérico de leucócitos em µL", examples=["10000"])
    linfocitos: str = Field(
        description="Valor numérico de linfócitos em µL", examples=["10000"])
    monocitos: str = Field(
        description="Valor numérico de monócitos em µL", examples=["10000"])
    neutrofilos: str = Field(
        description="Valor numérico de neutrófilos em µL", examples=["10000"])
    # esquizocitos: str = Field(description="Valor booleano de esquizócitos")


def convert_to_float(value):
    try:
        return float(value)
    except:
        return None


def convert_to_int(value):
    try:
        return int(value)
    except:
        return None


def chain_structured_invoke(docs):

    # Prompt
    system = """Você vai receber um documento em PDF com os resultados de um exame de hemograma e outros. Foque somente no exame de hemograma."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),

            ("human", "Exame completo: {exame}"),
        ]
    )

    llm_with_tools = llm.bind_tools([GetSchema])  # , strict=True)
    chain_structured = prompt | llm_with_tools

    response = chain_structured.invoke({"exame": docs})
    return response


def formated_docs(docs):
    return "\n\n".join([doc.text for doc in docs])


def format_docs_search(docs):
    return "\n\n".join([doc.page_content for doc in docs])


def chain_diagnostico(plaquetas=0, hemoglobina=0, neutrofilos=0, linfocitos=0, vcm=0, vmc=0, vpm=0, macroplaquetas=0, medicacao=0, infeccao=0, idade=0, sexo=0, data=0, leucocitos=0, chcm=0):
    base_rule = "Você é um assistente de médico que irá ajudar montar o diagnóstico do paciente baseado no hemograma."
    
    query = f"O paciente tem {idade} anos, é do sexo {sexo}, e fez o exame no dia {data}. Os resultados do hemograma são: Plaquetas: {plaquetas}, Hemoglobina: {hemoglobina}, Neutrófilos: {neutrofilos}, Linfócitos: {linfocitos}, VCM: {vcm}, VMC: {vmc}, VPM: {vpm}, Macroplaquetas: {macroplaquetas}, Medicação: {medicacao}, Infecção: {infeccao}"
    docs = vectorstore.similarity_search(query, k=10)
    docs_str = format_docs_search(docs)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", base_rule),
            ("system",f"O paciente tem {idade} anos, é do sexo {sexo}, e fez o exame no dia {data}."),
            ("system", "Os resultados do hemograma são:"),
            ("system", f"Resultado: {query}"),
            ("system",f"Baseie o diagnóstico dos seguintes documentos de referência:\n{docs_str}"),
            ("human", "Diagnóstico do paciente com base nos resultados do hemograma é :"),
        ]
    )
    llm = ChatOpenAI(model = 'gpt-4-0125-preview')
    chain = (
        prompt
        | llm
        | StrOutputParser()
    )
    response = chain.invoke({})
    return response