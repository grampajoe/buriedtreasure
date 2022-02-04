FROM python:3.10

RUN useradd app

USER app
WORKDIR /home/app

ADD --chown=app:app requirements.txt /home/app/
RUN pip install -r requirements.txt

ENV PATH="/home/app/.local/bin:${PATH}"

ADD --chown=app:app . /home/app/

ENV WEB_WORKERS=1
ENV CELERY_WORKERS=1

CMD ["honcho", "start"]
