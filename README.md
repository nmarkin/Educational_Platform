**Структура Курса:**

app_simple.py - flask сервер с обработкой запросов из js, роутами и прочим..

**templates/ - HTML страницы**

-- view - Шаблон страницы курса, динамически генерирует блоки theory/test/text 

-- profile - страница со списком курсов

-- download - страница генерации новых курсов

**static/**

**--js/ - скрипты**

---- upload.js - для работы с download

---- blocks.js - для view

**-- courses/ - папка с курсами, сюда попадают и новые сгенерированные**

---- courses.json - краткая инфа по курсам

**---- course_i/ - папка курса**

------ contents.json - оглавление

------ pages/ - папка с json-ами по страницам

------ downloads/ - все файлы которые загрузили при генерации курса

------ course.txt - саммари по загруженным файлам
