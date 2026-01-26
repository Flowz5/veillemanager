FROM python:3.9-slim
WORKDIR /app
RUN pip install discord.py python-dotenv
COPY bot.py .
CMD ["python", "bot.py"]