FROM python:3.11-slim-bookworm

ENV GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no"

RUN apt-get update \
    && apt-get install -y libgl1 libglib2.0-0 curl wget git \
    && apt-get clean

RUN pip install --no-cache-dir docling

ENV HF_HOME=/tmp/
ENV TORCH_HOME=/tmp/

COPY examples/minimal.py /root/minimal.py

RUN python -c 'from deepsearch_glm.utils.load_pretrained_models import load_pretrained_nlp_models; load_pretrained_nlp_models(verbose=True);'
RUN python -c 'from docling.document_converter import DocumentConverter; artifacts_path = DocumentConverter.download_models_hf(force=True);'
RUN wget "https://www.ibm.com/docs/en/SSQRB8/com.ibm.spectrum.si.pdfs/IBM_Storage_Insights_Fact_Sheet.pdf" -O /root/factsheet.pdf

# On container shell:
# > cd /root/
# > python minimal.py
