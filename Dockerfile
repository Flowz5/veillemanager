FROM python:3.9-slim
WORKDIR /app
RUN pip install discord.py python-dotenv requests beautifulsoup4 mysql-connector-python rich lxml
COPY bot.py .
CMD ["python", "bot.py"]