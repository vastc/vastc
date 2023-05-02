FROM nvidia/cuda:11.4.1-base-ubuntu20.04

WORKDIR /app

RUN apt-get update && apt-get install -y python3 python3-pip curl git
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-17-jre-headless

RUN pip3 install torch torchvision torchaudio
RUN pip3 install nnunet

ENV nnUNet_raw_data_base="/app/nnUNet_raw" nnUNet_preprocessed="/app/nnUNet_preprocessed" RESULTS_FOLDER="/app/nnUNet_results"
RUN nnUNet_download_pretrained_model Task009_Spleen

RUN curl -L -o dcm4che-5.29.2-bin.tar.gz 'https://sourceforge.net/projects/dcm4che/files/dcm4che3/5.29.2/dcm4che-5.29.2-bin.tar.gz' && tar xvf dcm4che-5.29.2-bin.tar.gz && mv -v dcm4che-5.29.2 dcm4che && rm -f dcm4che-5.29.2-bin.tar.gz

RUN curl -L -o dcmqi-1.2.5-linux.tar.gz 'https://github.com/QIICR/dcmqi/releases/download/v1.2.5/dcmqi-1.2.5-linux.tar.gz' && tar xvf dcmqi-1.2.5-linux.tar.gz && mv -v dcmqi-1.2.5-linux dcmqi && rm -f dcmqi-1.2.5-linux.tar.gz

COPY requirements.txt /app
COPY *.py /app
COPY spleen.json /app
RUN pip3 install -r requirements.txt

CMD [ "python3", "main_pipeline_w_spleen_segmentaion_03_09.py" ] 
