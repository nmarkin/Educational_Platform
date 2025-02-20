from flask import Flask, render_template, url_for
import os
import re
import json
import textract
import tiktoken
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import request, jsonify, redirect
from openai import OpenAI
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"),)
app = Flask(__name__, static_folder='static')
BASE_COURSES_DIR = "static\\courses"
os.makedirs(BASE_COURSES_DIR, exist_ok=True)
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")

current_course_id = None
context_retriever = None

def fetch_image_url(keyword):
    """Запрашивает Unsplash API и возвращает URL первой найденной картинки."""
    url = f"https://api.unsplash.com/search/photos?query={keyword}&orientation=landscape&content_filter=high&client_id={UNSPLASH_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data["results"]:
            return data["results"][0]["urls"]["small"]
    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
    return None

def get_next_course_number():
    """Определяет следующий номер для новой папки course_N."""
    existing_folders = [f for f in os.listdir(BASE_COURSES_DIR) if re.match(r"course_\d+", f)]
    numbers = [int(f.split("_")[1]) for f in existing_folders if f.split("_")[1].isdigit()]
    return max(numbers, default=0) + 1

# def cleanup_old_files():
#     """Удаляет самые старые файлы, если их больше 95 (оставляем запас)."""
#     try:
#         file_list = client.files.list()  # Получаем список файлов
#         if len(file_list.data) >= 95:  # Оставляем небольшой запас, чтобы не упереться в лимит
#             sorted_files = sorted(file_list.data, key=lambda f: f["created_at"])  # Сортируем по дате
#             for file in sorted_files[:len(file_list.data) - 95]:  # Удаляем самые старые файлы
#                 client.files.delete(file["id"])
#                 print(f"Удален файл: {file['id']} (старый)")
#     except Exception as e:
#         print(f"Ошибка при удалении старых файлов: {e}")

# def upload_files_to_openai(file_paths):
#     """Загружает файлы в OpenAI, удаляя старые при необходимости."""
#     cleanup_old_files()  # Удаляем старые файлы перед загрузкой
    
#     file_ids = []
#     for file_path in file_paths:
#         try:
#             with open(file_path, "rb") as f:
#                 response = client.files.create(
#                     file=f,
#                     purpose="assistants"
#                 )
#                 file_ids.append(response.id)  # Сохраняем file_id
#                 print(f"Загружен файл: {file_path} → {response.id}")
#         except Exception as e:
#             print(f"Ошибка загрузки файла {file_path}: {e}")
#     return file_ids

def count_tokens(text):
    """Возвращает количество токенов в тексте."""
    enc = tiktoken.encoding_for_model("gpt-4o")
    return len(enc.encode(text))

def split_text_to_chunks(text, max_tokens=100000):
    """Разбивает текст на части, если он слишком длинный."""
    enc = tiktoken.encoding_for_model("gpt-4o")
    tokens = enc.encode(text)

    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk = enc.decode(tokens[i:i + max_tokens])
        chunks.append(chunk)

    return chunks

def extract_text_from_files(file_paths):
    """Читает текст из файлов, используя `open()` для `.txt` и `textract` для сложных форматов."""
    extracted_texts = []
    
    for file_path in file_paths:
        try:
            if file_path.endswith(".txt"):
                # Читаем .txt файлы напрямую
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="utf-8-sig") as f:
                        text = f.read()
            else:
                # Используем textract для сложных файлов
                text = textract.process(file_path).decode("utf-8")

            chunks = split_text_to_chunks(text)
            for i, chunk in enumerate(chunks):
                extracted_texts.append((f"{file_path}_part_{i+1}", chunk))

        except Exception as e:
            print(f"Ошибка при обработке {file_path}: {e}")
            continue  # Пропускаем файл, если не удается прочитать

    return extracted_texts

def load_main_context(path):
    """Загружает и индексирует основной контекст из файла course.txt"""
    global context_retriever
    course_file_path = os.path.join(path, 'course.txt')

    try:
        with open(course_file_path, 'r', encoding='utf-8') as f:
            course_content = f.read()

        # Разбиваем текст на части
        splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        documents = splitter.split_text(course_content)

        # Преобразуем в объекты Document
        docs = [Document(page_content=chunk) for chunk in documents]

        # Создаём FAISS-индекс
        embeddings = OpenAIEmbeddings()
        context_retriever = FAISS.from_documents(docs, embeddings)

    except FileNotFoundError:
        print("Файл course.txt не найден. Убедитесь, что он лежит в static.")
    except Exception as e:
        print(f"Ошибка при обработке course.txt: {e}")

# Создание векторного хранилища

def create_vector_store_from_pages(directory):
    documents = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                page_content = json.load(file)
                for task in page_content.get("tasks", []):
                    content = task.get("content", "")
                    if isinstance(content, str):
                        documents.append(Document(page_content=content, metadata={"source": filename}))
                    elif isinstance(content, list):
                        for item in content:
                            condition = item.get("condition", "")
                            documents.append(Document(page_content=condition, metadata={"source": filename}))

    splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
    split_docs = splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings()
    return FAISS.from_documents(split_docs, embeddings)


def find_similar_chunks(chunks, threshold=0.8):
    """Находит похожие текстовые куски и группирует их для объединения."""
    vectorizer = TfidfVectorizer().fit_transform(chunks)
    vectors = vectorizer.toarray()
    
    merged_chunks = []
    used_indices = set()

    for i, chunk in enumerate(chunks):
        if i in used_indices:
            continue
        
        similar_group = [chunk]  # Начинаем группу похожих кусков
        used_indices.add(i)

        for j, other_chunk in enumerate(chunks):
            if j != i and j not in used_indices:
                similarity = cosine_similarity([vectors[i]], [vectors[j]])[0][0]
                if similarity > threshold:
                    similar_group.append(other_chunk)
                    used_indices.add(j)

        merged_chunks.append(similar_group)

    return merged_chunks  # Возвращаем списки схожих кусков

def merge_chunks_with_gpt(similar_chunks):
    """Объединяет похожие текстовые куски через GPT, сохраняя уникальную информацию."""
    merged_texts = []
    
    for group in similar_chunks:
        if len(group) == 1:
            merged_texts.append(group[0])  # Если кусок уникальный, просто сохраняем
            continue

        prompt = f"""
        Ты помощник по обработке учебных материалов.

        У тебя есть несколько фрагментов текста, которые описывают одно и то же, но могут содержать разные важные детали.
        Твоя задача — объединить их в один, сохранив ВСЮ уникальную информацию.

        Вот фрагменты:
        {{"\n\n---\n\n".join(group)}}

        Объединенный текст:
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Ты помощник в обработке текстов."},
                      {"role": "user", "content": prompt}]
        )

        try:
            merged_texts.append(response.choices[0].message.content)
        except Exception as e:
            print(f"Ошибка при объединении фрагментов: {e}")
            merged_texts.append("\n\n".join(group))  # Если GPT не сработал, просто склеиваем
    
    return merged_texts  # Возвращаем объединенные куски

def create_course_context(file_paths, output_path):
    """Создает course.txt, объединяя похожие куски перед записью."""
    all_chunks = []

    if len(file_paths) == 1: 

        try:
            file_path = file_paths[0]
            if file_path.endswith(".txt"):
                # Читаем .txt файлы напрямую
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="utf-8-sig") as f:
                        text = f.read()
            else:
                # Используем textract для сложных файлов
                text = textract.process(file_path).decode("utf-8")
        except Exception as e:
            print(f"Ошибка при чтении {file_path}: {e}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(text))

        print(f"Контекст сохранен в {output_path}")

    else:
        # **ШАГ 1: Читаем файлы и разбиваем их на части**
        for file_path in file_paths:
            try:
                if file_path.endswith(".txt"):
                    # Читаем .txt файлы напрямую
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            text = f.read()
                    except UnicodeDecodeError:
                        with open(file_path, "r", encoding="utf-8-sig") as f:
                            text = f.read()
                else:
                    # Используем textract для сложных файлов
                    text = textract.process(file_path).decode("utf-8")

                    
                    # Разбиваем текст на части по 2000 символов с overlap 200
                    chunks = [text[i:i + 2000] for i in range(0, len(text), 1800)]
                    
                    all_chunks.extend(chunks)
            except Exception as e:
                print(f"Ошибка при чтении {file_path}: {e}")

        # **ШАГ 2: Находим схожие фрагменты**
        similar_chunks = find_similar_chunks(all_chunks)

        # **ШАГ 3: Объединяем схожие куски с помощью GPT**
        unique_chunks = merge_chunks_with_gpt(similar_chunks)

        # **ШАГ 4: Записываем в course.txt**
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(unique_chunks))

        print(f"Контекст сохранен в {output_path}")


@app.route("/")
def home():
    # return render_template('download.html')
    return redirect(url_for('profile'))


@app.route("/api/get_next_course_number", methods=["GET"])
def api_get_next_course_number():
    """Возвращает следующий номер курса (для JS)."""
    course_number = get_next_course_number()
    return jsonify({"course_number": course_number})


@app.route("/upload", methods=["POST"])
def upload_file():
    """Загружает файлы в курс с фиксированным номером."""
    if "file" not in request.files or "course_number" not in request.form:
        return jsonify({"error": "Некорректные данные"}), 400

    file = request.files["file"]
    course_number = request.form["course_number"]

    course_folder = os.path.join(BASE_COURSES_DIR, f"course_{course_number}", "downloads")
    os.makedirs(course_folder, exist_ok=True)

    file_path = os.path.join(course_folder, file.filename)
    file.save(file_path)

    return jsonify({
        "message": "Файл загружен",
        "file_path": file_path,
        "course_folder": course_folder
    }), 200


def generate_chapter_structure(file_name, file_text, description, intensity):
    """Создает структуру глав для одного файла с учетом описания курса и уровня детализации."""
    prompt = f"""
    Ты помощник по созданию учебных курсов.

    Раздели этот текст на главы, сохранив логическую структуру.  
    Учитывай описание курса: "{description}".  
    Уровень детализации: {intensity} (1 - краткий, 2 - стандартный, 3 - углубленный).

    - Если {intensity} = 1, делай главы сокращенными и не углубляйся в мелкие детали.  
    - Если {intensity} = 2, делай стандартные главы, полностью сохрани весь оригинальный текст
    - Если {intensity} = 3, полностью сохрани весь оригинальный текст и добавляй дополнительные детали, включая примеры.

    Формат ответа строго в формате JSON по примеру:
    {{
        "chapters": [
            {{
                "title": "Емкое название главы",
                "start": 0,
                "end": 5000,
                "summary": "Краткое описание содержания с основными пунктами",
                "source": "{file_name}"
            }}
        ]
    }}

    Вот текст:
    "{file_text}"
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Ты помощник в создании учебных курсов."},
                  {"role": "user", "content": prompt}]
    )

    generated_content = response.choices[0].message.content

    if generated_content.startswith("```json") and generated_content.endswith("```"):
            generated_content = generated_content[7:-3].strip()

    try:
        return json.loads(generated_content)
    except json.JSONDecodeError:
        return None

    

def merge_chapter_structures(chapter_lists, description, intensity):
    """Объединяет главы из всех файлов, убирает дубликаты с учетом уровня детализации."""
    prompt = f"""
    Ты помощник по созданию структуры учебного курса.

    Перед тобой списки глав из нескольких источников.  
    Некоторые главы могут быть одинаковыми по сути, но с разными названиями.  
    Объедини их в одну, если они содержат одинаковую или схожую информацию.
    Обязательно сохрани всю информацию из обьединенных глав, которая не повторялась между ними

    Основывайся на описании курса: "{description}".  
    Уровень детализации: {intensity} (1 - краткий, 2 - стандартный, 3 - углубленный).

    - Если {intensity} = 1, объединяй главы и оставляй только самые важные темы.
    - Если {intensity} = 2 или 3, сохраняй все основные главы, объединяй только почти идентичные главы. 

    Вот списки глав:
    {json.dumps(chapter_lists, ensure_ascii=False, indent=4)}


    Выдай итоговое оглавление строго в формате JSON по образцу:
    {{
        "chapters": [
            {{
                "title": "Название объединенной главы",
                "summary": "<p>Краткое описание содержания главы</p>",
                "source": ["file_1_part_1", "file_2_part_1"]
            }}
        ]
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Ты помощник в создании учебных курсов."},
                  {"role": "user", "content": prompt}]
    )

    generated_content = response.choices[0].message.content
    

    if generated_content.startswith("```json") and generated_content.endswith("```"):
            generated_content = generated_content[7:-3].strip()
    try:
        # print(generated_content)
        merged_chapters = json.loads(generated_content)["chapters"]
    except json.JSONDecodeError:
        return None

    # **ШАГ 2: Добавляем `id` и `path` вручную**
    for idx, chapter in enumerate(merged_chapters, start=1):
        chapter["id"] = idx
        chapter["path"] = f"page_{idx}"

    return {"chapters": merged_chapters}

    

@app.route("/api/generate_contents", methods=["POST"])
def generate_contents():
    data = request.json
    course_number = data.get("course_number")
    course_name = data.get("course_name", "Новый курс")
    description = data.get("description", "")
    intensity = data.get("intensity", "2")
    files = data.get("files", [])

    if not course_number:
        return jsonify({"error": "Отсутствует номер курса"}), 400

    course_folder = os.path.join(BASE_COURSES_DIR, f"course_{course_number}")
    downloads_folder = os.path.join(course_folder, "downloads")
    os.makedirs(downloads_folder, exist_ok=True)

    file_paths = [os.path.join(downloads_folder, f) for f in files]
    file_texts = extract_text_from_files(file_paths)

    # **ШАГ 1: Генерируем `contents.json` для каждого файла**
    chapter_lists = []
    for file_name, file_text in file_texts:
        chapter_structure = generate_chapter_structure(file_name, file_text, description, intensity)
        if chapter_structure:
            chapter_lists.append(chapter_structure)

    # **ШАГ 2: Объединяем главы через GPT**
    merged_structure = merge_chapter_structures(chapter_lists, description, intensity)

    if not merged_structure:
        return jsonify({"error": "Ошибка объединения глав"}), 500

    # **ШАГ 3: Сохраняем финальный `contents.json`**
    contents_path = os.path.join(course_folder, "contents.json")
    with open(contents_path, "w", encoding="utf-8") as f:
        json.dump(merged_structure, f, ensure_ascii=False, indent=4)

     # **ШАГ 4: Создаем `course.txt` (удаляем дубликаты)**
    course_txt_path = os.path.join(course_folder, "course.txt")
    create_course_context(file_paths, output_path=course_txt_path)

    return jsonify({"message": "Файл contents.json создан", "course_folder": f"course_{course_number}"})


@app.route("/course/<course_id>/module/<int:page_id>")
def view(course_id, page_id):
    course_path = os.path.join(app.static_folder, f'courses\\{course_id}')
    course_num = int(course_id.split('_')[-1])

    global current_course_id

    # Проверяем, загружен ли уже нужный курс
    if current_course_id != course_id:
        try:
            # Загружаем контекст только если курс изменился
            load_main_context(course_path)
            current_course_id = course_id
            print(f"Контекст курса {course_id} загружен.")  # Логирование смены курса
        except FileNotFoundError:
            return f"Контекст для проекта {course_id} не найден.", 404
        except Exception as e:
            return f"Ошибка при загрузке контекста проекта {course_id}: {e}", 500

    courses_file = os.path.join(app.static_folder, 'courses/courses.json')
    with open(courses_file, 'r', encoding='utf-8') as f:
        courses = json.load(f).get("courses", [])

    chapters_file = os.path.join(course_path, 'contents.json')
    with open(chapters_file, 'r', encoding='utf-8') as f:
        chapters = json.load(f).get("chapters", [])

    pages_dir = os.path.join(course_path, 'pages')
    if not os.path.exists(pages_dir):
        return "Страницы для курса не найдены.", 404

    # Получаем только одну страницу по page_id
    try:
        page_file = sorted(os.listdir(pages_dir), key=lambda x: int(x.split('_')[1].split('.')[0]))[page_id - 1]
        with open(os.path.join(pages_dir, page_file), 'r', encoding='utf-8') as file:
            page = json.load(file)
    except (IndexError, FileNotFoundError):
        return "Страница не найдена.", 404

    return render_template("view.html", course=courses[course_num-1], page=page, chapters=chapters, chapter_title=chapters[page_id - 1]['title'])


# @app.route("/api/chat", methods=["POST"])
# def chat():
#     global vector_store
#     data = request.json
#     user_message = data.get("message")
#     print(f"User message: {user_message}")
#     model = ChatOpenAI(model="gpt-4o-mini", stream=False)

#     try:
#         system_prompt = (
#             "Ты являешься цифровым помощником для работы с учебным курсом. "
#             "Отвечай на вопросы, используя информацию из контекста. "
#             "Если ответа на вопрос нет, ответь, что не можешь предоставить информацию.\n\n{context}"
#         )

#         retriever = vector_store.as_retriever()
#         prompt = ChatPromptTemplate.from_messages(
#             [("system", system_prompt), ("human", "{input}")]
#         )
#         question_answer_chain = create_stuff_documents_chain(model, prompt)
#         rag_chain = create_retrieval_chain(retriever, question_answer_chain)

#         result = rag_chain.invoke({"input": user_message})

#         if isinstance(result, Document):
#             reply_content = result.page_content
#         elif isinstance(result, dict):
#             reply_content = result.get("answer", "Ответ не найден.")
#         else:
#             reply_content = str(result)

#         return jsonify({"reply": reply_content})
#     except Exception as e:
#         return jsonify({"reply": f"Ошибка обработки запроса: {str(e)}"}), 500



@app.route("/api/check_text_answer", methods=["POST"])
def check_text_answer():
    try:
        data = request.json
        user_answer = data.get("user_answer", "").strip()
        correct_answer = data.get("correct_answer", "").strip()
        task_title = data.get("task_title", "Задание")

        # Подключаем ИИ для проверки ответа
        model = ChatOpenAI(model="gpt-4o-mini", stream=False)
        
        # Создаем сообщения в правильном формате
        messages = [
            {"role": "system", "content": "Ты помощник для проверки заданий. Твоя задача — сравнить ответ ученика с правильным ответом, оценить его как Правильно/Неправильно и предоставить комментарий. Сначала выведи одно слово Правильно или Неправильно, а затем с новой строчки комментарий"},
            {"role": "user", "content": f"Название задания: {task_title}\nПравильный ответ: {correct_answer}\nОтвет ученика: {user_answer}\n\nКомментарий:"}
        ]

        # Вызываем модель
        result = model(messages)
        
        # Извлекаем текст комментария из AIMessage
        comment = result.content if hasattr(result, "content") else "Ошибка обработки ответа."
        correct = 1 if comment.split()[0] == 'Правильно' else 0

        return jsonify({"comment": comment, "correct": correct})
    except Exception as e:
        return jsonify({"error": f"Ошибка обработки запроса: {str(e)}"}), 500
    
@app.route("/api/generate_block", methods=["POST"])
def generate_block():
    try:
        data = request.json
        user_input = data.get("question", "").strip()
        block_context = data.get("context", "").strip()

        if not user_input:
            return jsonify({"error": "Вопрос отсутствует"}), 400

        if not context_retriever:
            return jsonify({"error": "Ретривер контекста не настроен"}), 500

        # Объединяем ввод пользователя и контекст блока
        search_query = f"{block_context}\n\n{user_input}" if block_context else user_input

        # Извлекаем релевантные фрагменты из общего контекста
        relevant_docs = context_retriever.similarity_search(search_query, k=3)
        retrieved_context = "\n\n".join([doc.page_content for doc in relevant_docs])

        # Если ничего не найдено, fallback на блок или общее сообщение
        if not relevant_docs:
            if block_context:
                retrieved_context = block_context
            else:
                retrieved_context = "Контекст не найден. Ответь на вопрос как можно лучше без контекста."

        # Генерация запроса для OpenAI
        if "Подробнее" in user_input:
            system_prompt = (
                f"Ты помощник для генерации контента. "
                f"Расширь текст только текущего блока, без добавления информации из других частей курса. "
                f"Сделай текст текущего блока более подробным.Вот его текст:\n\n{block_context}\n\n"
                f"Можешь воспользоавться контекстом курса - :\n\n{retrieved_context}\n\n, в случае крайней необходимости"
                f"Обязательно отформатируй текст в HTML с заголовками (не больше h3), списками и параграфами, если это уместно."
                f"Ответ должен быть не более 200 слов"
            )
        else:
            system_prompt = (
                f"Ты помощник для ответа на вопросы. Ответь на следующий вопрос на основе контекста. "
                f"Обязательно отформатируй ответ в HTML с заголовками (не больше h3), списками и параграфами, если это уместно. (не более 200 слов)"
                f"Можешь воспользоавться контекстом курса - :\n\n{retrieved_context}\n\n, в случае крайней необходимости"
                f"Вопрос: {user_input}\n"
            )

        model = ChatOpenAI(model="gpt-4o-mini", stream=False, max_tokens=500)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        # Генерация ответа
        result = model(messages)

        generated_title = user_input  # Используем вопрос как заголовок
        generated_content = result.content if hasattr(result, "content") else "Ошибка в генерации контента."

        if generated_content.startswith("```html") and generated_content.endswith("```"):
            generated_content = generated_content[7:-3].strip()

        return jsonify({
            "title": generated_title,
            "content": generated_content
        })

    except Exception as e:
        return jsonify({"error": f"Ошибка обработки запроса: {str(e)}"}), 500
    
    
@app.route("/api/generate_explanation", methods=["POST"])
def generate_explanation():
    try:
        data = request.json
        task_title = data.get("task_title", "Задание")
        is_correct = data.get("is_correct", False)
        test_answers = data.get("test_answers", [])
        text_answers = data.get("text_answers", [])

        # Формируем контекст для генерации объяснения
        explanation_prompt = f"Разбор задания: {task_title}\n\n"
        if is_correct:
            explanation_prompt += "Поздравляем! Вы справились с этим заданием. Объясните, почему все ответы правильные:\n\n"
        else:
            explanation_prompt += "Некоторые ответы неверны. Объясните правильные ответы и разберите ошибки пользователя:\n\n"

        # Добавляем разбор тестов
        if test_answers:
            explanation_prompt += "Ответы на тестовые вопросы:\n"
            for answer in test_answers:
                explanation_prompt += f"- Вопрос: {answer['condition']}\n"
                explanation_prompt += f"  Ваш ответ: {'Да' if answer['userAnswer'] else 'Нет'}\n"
                explanation_prompt += f"  Правильный ответ: {'Да' if answer['correctAnswer'] else 'Нет'}\n"

        # Добавляем разбор текстовых ответов
        if text_answers:
            explanation_prompt += "\nОтветы на текстовые задания:\n"
            for answer in text_answers:
                explanation_prompt += f"- Ваш ответ: {answer['userAnswer']}\n"
                explanation_prompt += f"  Правильный ответ: {answer['correctAnswer']}\n"

        explanation_prompt += "\nДайте краткое, но детальное объяснение правильных ответов."


        # Извлекаем релевантные фрагменты из общего контекста
        relevant_docs = context_retriever.similarity_search(task_title, k=3)
        retrieved_context = "\n\n".join([doc.page_content for doc in relevant_docs])

        # Если ничего не найдено, fallback на блок или общее сообщение
        if not relevant_docs:
            retrieved_context = "Контекст не найден. Ответь на вопрос как можно лучше без контекста."

        system_prompt = (
            f"Ты помощник для генерации разборов заданий."
            f"Обязательно отформатируй текст в HTML с заголовками (не больше h3), списками, шрифтами и параграфами, если это уместно."
            f"В качестве контекста для объяснения можешь использовать следующий материал :\n\n{retrieved_context}"
            f"Ответ должен быть не более 200 слов"
        )

        # Отправка запроса к OpenAI
        model = ChatOpenAI(model="gpt-4o-mini", stream=False, max_tokens=600)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": explanation_prompt},
        ]
        result = model(messages)

        explanation = result.content if hasattr(result, "content") else "Ошибка в генерации объяснения."

        if explanation.startswith("```html") and explanation.endswith("```"):
            explanation = explanation[7:-3].strip()

        return jsonify({"explanation": explanation})

    except Exception as e:
        return jsonify({"error": f"Ошибка обработки запроса: {str(e)}"}), 500

@app.route("/api/update_chapter_title", methods=["POST"])
def update_chapter_title():
    data = request.json
    course_folder = data.get("course_folder")
    chapter_id = data.get("chapter_id")
    new_title = data.get("new_title")

    if not course_folder or not chapter_id or not new_title:
        return jsonify({"error": "Некорректные данные"}), 400

    contents_path = os.path.join(BASE_COURSES_DIR, course_folder, "contents.json")

    try:
        with open(contents_path, "r", encoding="utf-8") as f:
            contents = json.load(f)

        for chapter in contents["chapters"]:
            if chapter["id"] == int(chapter_id):
                chapter["title"] = new_title

        with open(contents_path, "w", encoding="utf-8") as f:
            json.dump(contents, f, ensure_ascii=False, indent=4)

        return jsonify({"message": "Название главы обновлено"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/publish_course", methods=["POST"])
def publish_course():
    """Генерирует страницы для курса и публикует его, записывая информацию в courses.json."""
    data = request.json.get("requestData")
    course_folder = data.get("course_folder")
    course_name = data.get("course_name")
    course_description = data.get("description")
    intensity = data.get("intensity")

    # print(course_folder, course_name)

    if not course_folder or not course_name:
        return jsonify({"error": "Не указан курс или название"}), 400

    contents_path = os.path.join(BASE_COURSES_DIR, course_folder, "contents.json")
    pages_folder = os.path.join(BASE_COURSES_DIR, course_folder, "pages")
    downloads_folder = os.path.join(BASE_COURSES_DIR, course_folder, "downloads")
    os.makedirs(pages_folder, exist_ok=True)

    try:
        with open(contents_path, "r", encoding="utf-8") as f:
            contents = json.load(f)

        # Читаем все файлы и разбиваем на чанки
        file_paths = [os.path.join(downloads_folder, f) for f in os.listdir(downloads_folder)]
        file_texts = extract_text_from_files(file_paths)  # Используем уже готовую функцию

        # Генерируем страницы для каждой главы
        for chapter in contents["chapters"]:
            page_path = os.path.join(pages_folder, f"page_{chapter['id']}.json")

            # Генерируем содержимое главы с учетом источников (source)
            generated_page = generate_chapter_content(chapter["title"], chapter["summary"], chapter.get("source", []), file_texts, intensity, course_description)

            # Заменяем image_keywords на image_url
            for task in generated_page.get("tasks", []):
                if task.get("task_type") == "theory" and "image_keywords" in task:
                    image_url = fetch_image_url(task["image_keywords"]) 
                    if image_url:
                        task["image_url"] = image_url

            with open(page_path, "w", encoding="utf-8") as f:
                json.dump(generated_page, f, ensure_ascii=False, indent=4)

        # Записываем информацию о курсе в courses.json
        courses_json_path = os.path.join(BASE_COURSES_DIR, "courses.json")

        # Проверяем, существует ли файл
        if os.path.exists(courses_json_path):
            with open(courses_json_path, "r", encoding="utf-8") as f:
                courses_data = json.load(f)
        else:
            courses_data = {"courses": []}  # Если файла нет, создаем пустую структуру

        # Новый курс
        new_course = {
            "id": f"course_{course_folder.split('_')[1]}",
            "title": course_name,
            "path": f"courses/{course_folder}/",
            "description": course_description
        }

        # Добавляем в список курсов
        courses_data["courses"].append(new_course)

        # Записываем обратно в файл
        with open(courses_json_path, "w", encoding="utf-8") as f:
            json.dump(courses_data, f, ensure_ascii=False, indent=4)

        return jsonify({"message": "Курс опубликован", "redirect_url": f"/course/{course_folder}/module/1"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



def generate_chapter_content(title, summary, sources, file_texts, intensity, course_description):
    """Генерирует содержимое главы, используя текстовые чанки из source и параметры интенсивности и описания курса."""
    
    # Получаем текстовые чанки, которые относятся к главе
    relevant_chunks = []
    for file_name, file_text in file_texts:
        if any(source in file_name for source in sources):  # Если чанк указан в source, добавляем его в контекст
            relevant_chunks.append(file_text)

    context_text = "\n\n".join(relevant_chunks[:3])  # Берем максимум 3 чанка, чтобы не перегружать GPT

    if intensity == '1':
        intensity = 'Сделай емкую детальную выжимку контекста.'
    elif intensity == '2':
        intensity = 'Сделай главу дословным пересказом контекста.'
    else:
        intensity = 'Сделай главу подробным пересказом контекста, можешь сам его дополнить релеванитой информацией или примерами.'

    # prompt = f"""
    #     Ты помощник по созданию учебных курсов.

    #     Создай учебный материал для главы "{title}".
    #     Описание главы: "{summary}"

    #     Интенсивность курса: {intensity}
    #     Описание курса: "{course_description}"

    #     Используй следующий контекст из загруженных файлов:
    #     "{context_text}"

    #     Требования к структуре:
    #     - **Сначала идут блоки `theory`**. Если глава большая, раздели ее на несколько логически связанных частей. Можешь использовать HTML разметку для оформления текста в content
    #     - **К самым важным `theory`-блокам (не меньше одного на главу) добавь `image_keywords`** — список из 2-3 ключевых слов (на английском) для поиска изображения.
    #     - **Задания (`text` и `test`) добавляй только если это уместно** (например, если материал подразумевает проверку знаний).
    #     - **Если это введение, могут быть только `theory`-блоки без тестов и вопросов.**
    #     - **Тесты должны содержать варианты ответов с "+" (верный) и "-" (неверный)**.

    #     Выдай результат в формате JSON:
    #     {{
    #         "title": "{title}",
    #         "tasks": [
    #             {{
    #                 "title": "Название первой смысловой части главы",
    #                 "task_type": "theory",
    #                 "content": "Подробное объяснение первой ключевой мысли главы.",
    #                 "image_keywords": ["a query of keywords formal and professional"]
    #             }},
    #             {{
    #                 "title": "Название второй смысловой части главы",
    #                 "task_type": "theory",
    #                 "content": "Дополнительное объяснение другой важной мысли главы.",
    #                 "image_keywords": ["a query of keywords formal and professional"]
    #             }},
    #             {{
    #                 "title": "Тестовый вопрос",
    #                 "task_type": "test",
    #                 "content": [
    #                     {{
    #                         "condition": "Верный вариант ответа",
    #                         "answer": "+"
    #                     }},
    #                     {{
    #                         "condition": "Неверный вариант ответа",
    #                         "answer": "-"
    #                     }},
    #                     {{
    #                         "condition": "Неверный вариант ответа",
    #                         "answer": "-"
    #                     }},
    #                     {{
    #                         "condition": "Верный вариант ответа",
    #                         "answer": "+"
    #                     }},
    #                     ...
    #                 ]
    #             }},
    #             {{
    #                 "title": "Открытый вопрос к пользователю",
    #                 "task_type": "text",
    #                 "content": [
    #                     {{
    #                         "condition": "Какой главный вывод из этой главы?",
    #                         "answer": "Пример правильного ответа."
    #                     }}
    #                 ],
    #                 "hints": ["Подсказка 1", "Подсказка 2"]
    #             }}
    #         ]
    #     }}
    # """

    prompt = f"""
        Ты помощник по созданию учебных курсов.

        Создай учебный материал для главы **"{title}"**.
        Описание главы: "{summary}"

        **Формат курса**:
        - Интенсивность: "{intensity}"
        - Описание курса: "{course_description}"
        - Внимание: В описании курса могут быть особые требования к структуре глав (например, "только тесты", "только теория"). Учитывай их при создании материала.

        **Контекст из загруженных файлов** (используй его для написания содержания):
        "{context_text}"

        ---

        ### **Требования к структуре главы**:
        - Глава может включать в себя **любое количество `theory`-блоков**, если это уместно.
        - **Первым всегда идёт теоретический материал (`theory`)**. Если глава большая, раздели её на несколько логически связанных частей.
        - **К самым важным `theory`-блокам (не меньше одного на главу) добавь `image_keywords`** — список из 2-3 ключевых слов (на английском) для поиска изображения.
        - **После теории могут следовать задания (`text` и `test`), но они не обязательны**. Они должны быть только **если уместны**:
        - Если глава подразумевает проверку знаний — используй `test` или `text`.
        - Если в описании курса сказано, что он состоит **только из тестов** — используй **только `test`**.
        - Если курс **не предполагает проверочных вопросов**, включай **только `theory`**.
        - Если курс допускает **смешанный формат**, можешь использовать и `test`, и `text`, но **всегда после теории**.
        - **Тесты (`test`) должны содержать варианты ответов** с "+" (верный) и "-" (неверный).
        - **Задания `text` должны быть осмысленными**, а не искусственными. Если глава не предполагает открытых вопросов, не добавляй `text`.

        ---

        ### **Формат JSON** (пример, но НЕ строгий шаблон)
        **Важно:** Структура главы должна подстраиваться под её содержимое, а не жёстко следовать этому шаблону.

        Выдай результат в формате JSON:
        {{
            "title": "{title}",
            "tasks": [
                {{
                    "title": "Название первой смысловой части главы",
                    "task_type": "theory",
                    "content": "Подробное объяснение первой ключевой мысли главы.",
                    "image_keywords": ["a query of keywords formal and professional"]
                }},
                {{
                    "title": "Название второй смысловой части главы",
                    "task_type": "theory",
                    "content": "Дополнительное объяснение другой важной мысли главы.",
                    "image_keywords": ["a query of keywords formal and professional"]
                }},
                {{
                    "title": "Тестовый вопрос",
                    "task_type": "test",
                    "content": [
                        {{
                            "condition": "Верный вариант ответа",
                            "answer": "+"
                        }},
                        {{
                            "condition": "Неверный вариант ответа",
                            "answer": "-"
                        }},
                        {{
                            "condition": "Неверный вариант ответа",
                            "answer": "-"
                        }},
                        {{
                            "condition": "Верный вариант ответа",
                            "answer": "+"
                        }}
                    ]
                }},
                {{
                    "title": "Открытый вопрос к пользователю",
                    "task_type": "text",
                    "content": [
                        {{
                            "condition": "Какой главный вывод из этой главы?",
                            "answer": "Пример правильного ответа."
                        }}
                    ],
                    "hints": ["Подсказка 1", "Подсказка 2"]
                }}
            ]
        }}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Ты помощник в создании курсов."},
                  {"role": "user", "content": prompt}]
    )

    generated_content = response.choices[0].message.content

    if generated_content.startswith("```json") and generated_content.endswith("```"):
            generated_content = generated_content[7:-3].strip()

    try:
        return json.loads(generated_content)
    except json.JSONDecodeError:
        return {"title": title, "content": "Ошибка генерации контента", "questions": []}

@app.route("/api/course_materials/<course_id>")
def get_course_materials(course_id):
    # Папка с материалами курса
    course_path = f"static/courses/{course_id}/downloads"
    files = []

    if os.path.exists(course_path):
        for file in os.listdir(course_path):
            file_url = url_for('static', filename=f"courses/{course_id}/downloads/{file}")
            files.append({"name": file, "url": file_url})

    return jsonify({"materials": files})

# API для получения списка курсов
@app.route("/api/courses")
def get_courses():
    courses_path = "static/courses/courses.json"

    if not os.path.exists(courses_path):
        return jsonify({"courses": []})

    with open(courses_path, "r", encoding="utf-8") as file:
        courses = json.load(file)

    return jsonify(courses)

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/create_course')
def create_course():
    return render_template('download.html')

if __name__ == "__main__":
    app.run(debug=True, port=5002)
