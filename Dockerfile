FROM python:3
ADD bot.py /
RUN pip install asyncio
RUN pip install aqlite3
RUN pip install discord.py
RUN pip install datetime
CMD [ "python", "./bot.py" ]