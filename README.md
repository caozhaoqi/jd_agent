
## JD agent 


## use

- backend server install commandline

```commandline
uvicorn app.main:app --reload
pip install fastapi uvicorn langchain langchain-openai pydantic python-dotenv


```

- web

```shell
npx create-next-app@latest jd-chat-ui
cd jd-chat-ui
npm install react-markdown lucide-react clsx tailwind-merge
# 在 jd-chat-ui 目录下
npm install -D @tailwindcss/typography
npm install -D tailwindcss@3.4.17 postcss autoprefixer
#npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm run dev
```
