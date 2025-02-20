document.addEventListener("DOMContentLoaded", async () => {
    const materialsList = document.getElementById("materials-list");

    if (!materialsList || !window.courseId) return;

    try {
        const response = await fetch(`/api/course_materials/${window.courseId}`);
        const data = await response.json();

        materialsList.innerHTML = ""; // Очищаем сообщение "Загрузка..."

        if (data.materials.length === 0) {
            materialsList.innerHTML = "<p class='text-sm text-gray-500'>Файлы отсутствуют.</p>";
            return;
        }

        data.materials.forEach(file => {
            const fileLink = document.createElement("a");
            fileLink.href = file.url;
            fileLink.className = "flex items-center text-sm text-gray-600 hover:text-custom";
            fileLink.setAttribute("download", file.name);
            fileLink.innerHTML = `<i class="fas fa-file mr-2"></i>${file.name}`;
            
            materialsList.appendChild(fileLink);
        });

    } catch (error) {
        console.error("Ошибка загрузки материалов:", error);
        materialsList.innerHTML = "<p class='text-sm text-red-500'>Ошибка загрузки файлов.</p>";
    }
});


document.addEventListener("DOMContentLoaded", () => {

    const chapterProgress = {
        totalBlocks: document.querySelectorAll('.task-block').length,
        completedBlocks: 0
    };
    // const chapterNav = document.getElementById("chapter-nav");
    // const scrollLeft = document.getElementById("scroll-left");
    // const scrollRight = document.getElementById("scroll-right");

    // //  // Получаем текущий ID главы из URL
    // //  const urlParams = new URLSearchParams(window.location.search);
    // //  const currentPageId = urlParams.get("page_id");

    // // Получаем `page_id` из URL (для маршрутов вида `/course/1/module/3`)
    // const pathSegments = window.location.pathname.split('/');
    // const currentPageId = pathSegments[pathSegments.length - 1]; // Берём последний сегмент URL


    //  console.log("🔍 Текущий page_id из URL:", currentPageId);
 
    //  // Найти текущую главу в навигации
    //  const currentChapter = [...document.querySelectorAll('.chapter-link')]
    // .find(link => Number(link.dataset.page) === Number(currentPageId));
    
    // console.log("📌 Найденная текущая глава:", currentChapter);

    // document.querySelectorAll('.chapter-link').forEach(link => {
    //     console.log(`🔗 Глава: ${link.innerText}, data-page: ${link.dataset.page}`);
    // });
 
    //  if (currentChapter) {
    //      // Добавляем стили напрямую через JavaScript
    //      currentChapter.classList.add("current-chapter");
    //      currentChapter.style.color = "#1B9AF5"; // Голубой цвет текста
    //      currentChapter.style.borderBottom = "2px solid #1B9AF5"; // Голубая полоска снизу
    //      currentChapter.style.fontWeight = "600"; // Делаем жирным
 
    //      // Прокручиваем к текущей главе, чтобы она была в начале
    //      currentChapter.scrollIntoView({
    //          behavior: "smooth",
    //          block: "nearest",
    //          inline: "start"
    //      });
    //  }
 
    //  // Функция для обновления видимости кнопок прокрутки
    //  function updateScrollButtons() {
    //      scrollLeft.classList.toggle("hidden", chapterNav.scrollLeft === 0);
    //      scrollRight.classList.toggle("hidden", chapterNav.scrollLeft + chapterNav.clientWidth >= chapterNav.scrollWidth);
    //  }
 
    //  // Прокрутка влево
    //  scrollLeft.addEventListener("click", () => {
    //      chapterNav.scrollBy({ left: -200, behavior: "smooth" });
    //  });
 
    //  // Прокрутка вправо
    //  scrollRight.addEventListener("click", () => {
    //      chapterNav.scrollBy({ left: 200, behavior: "smooth" });
    //  });
 
    //  // Отслеживание изменений прокрутки
    //  chapterNav.addEventListener("scroll", updateScrollButtons);
 
    //  // Обновить кнопки при загрузке
    //  updateScrollButtons();

    // Обновление шкалы прогресса по главе
    function updateChapterProgress() {
        const progressPercentage = Math.round((chapterProgress.completedBlocks / chapterProgress.totalBlocks) * 100);
        document.getElementById('chapter-progress').textContent = `${progressPercentage}% Пройдено`;
        document.getElementById('chapter-progress-bar').style.width = `${progressPercentage}%`;
    }

    // Обработчик для кнопки "Подробнее"
    document.querySelectorAll("[data-toggle-input]").forEach(button => {
        button.addEventListener("click", () => {
            // Найти ближайший скрытый блок и показать его
            const inputBlock = button.closest("div").nextElementSibling;
            if (inputBlock.classList.contains("hidden")) {
                inputBlock.classList.remove("hidden");
            } else {
                inputBlock.classList.add("hidden");
            }
        });
    });

        // Обработчик для кнопки "Далее"
        document.addEventListener("click", async (event) => {
            if (event.target.classList.contains("next-button")) {
                event.preventDefault();
    
                // Найти текущий блок
                const taskBlock = event.target.closest('.task-block');
                if (!taskBlock) {
                    console.error("Не удалось найти родительский блок с классом '.task-block'.");
                    return;
                }
    
                // Выполнить проверку перед переходом
                const isTestCorrect = handleTestCheck(taskBlock);

                const isTextValid = validateTextFields(taskBlock);

                if (!isTextValid) {
                    alert("Пожалуйста, заполните все текстовые поля перед продолжением.");
                    return;
                }
                const isTextCorrect = await handleTextCheck(taskBlock);

                chapterProgress.completedBlocks++;
                updateChapterProgress();
    
                // Если проверка прошла, открыть следующий блок
                const nextBlockId = event.target.getAttribute("data-next");
                const nextBlock = document.getElementById(nextBlockId);
    
                if (nextBlock) {
                    nextBlock.classList.remove("hidden");
    
                    // Прокручиваем к следующему блоку
                    nextBlock.scrollIntoView({
                        behavior: "smooth", // Плавная прокрутка
                        block: "center"    // Центрируем блок в экране
                    });
                } else {
                    // Если следующий блок не найден, показываем сообщение "Глава пройдена!"
                    const chapterCompletedMessage = document.getElementById("chapter-completed");
                    if (chapterCompletedMessage) {
                        chapterCompletedMessage.classList.remove("hidden");
    
                        // Прокручиваем к сообщению "Глава пройдена!"
                        chapterCompletedMessage.scrollIntoView({
                            behavior: "smooth", // Плавная прокрутка
                            block: "center"    // Центрируем сообщение
                        });
                    }
                }
                event.target.disabled = true;
            }
        });
    
        // Обработчик для кнопки "Проверить"
        document.addEventListener("click", async (event) => {
            if (event.target.classList.contains("check-answers")) {
                event.preventDefault();
    
                const taskBlock = event.target.closest('.task-block');
                if (!taskBlock) {
                    console.error("Не удалось найти родительский блок с классом '.task-block'.");
                    return;
                }
    
                // Выполнить проверку
                const isTestCorrect = handleTestCheck(taskBlock);
                const isTextCorrect = await handleTextCheck(taskBlock);
    
                // Сгенерировать блок с объяснением (theory)
                generateExplanationBlock(taskBlock, isTestCorrect && isTextCorrect);
            }
        });
    
        // Проверка чекбоксов
        function handleTestCheck(taskBlock) {
            let isAllCorrect = true;
            const testInputs = taskBlock.querySelectorAll('input[type="checkbox"]');
    
            testInputs.forEach(input => {
                const isChecked = input.checked;
                const correctAnswer = input.dataset.answer === '+';
    
                let result = input.nextElementSibling;
                if (!result || !result.classList.contains('check-result')) {
                    result = document.createElement('span');
                    result.className = 'check-result ml-2 text-sm font-semibold';
                    input.parentElement.appendChild(result);
                }
    
                if (isChecked === correctAnswer) {
                    result.textContent = '✔ Правильно!';
                    result.style.color = 'green';
                } else {
                    result.textContent = '✘ Неправильно';
                    result.style.color = 'red';
                    isAllCorrect = false;
                }
            });
    
            return isAllCorrect;
        }
    
        // Проверка текстовых полей (на заполненность)
        function validateTextFields(taskBlock) {
            const textAreas = taskBlock.querySelectorAll('textarea');
            for (const textArea of textAreas) {
                if (!textArea.value.trim()) {
                    return false; // Если хотя бы одно поле пустое
                }
            }
            return true; // Все поля заполнены
        }

        // Проверка текстовых полей
        async function handleTextCheck(taskBlock) {
            let isAllCorrect = true;
            const textAreas = taskBlock.querySelectorAll('textarea');
    
            for (const textArea of textAreas) {
                const userAnswer = textArea.value.trim();
                const correctAnswer = textArea.dataset.answer.trim();
    
                if (!userAnswer) {
                    alert("Пожалуйста, введите ответ перед проверкой.");
                    isAllCorrect = false;
                    continue;
                }
    
                try {
                    const response = await fetch("/api/check_text_answer", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            user_answer: userAnswer,
                            correct_answer: correctAnswer,
                            task_title: taskBlock.querySelector('h2').textContent,
                        }),
                    });
    
                    const result = await response.json();
                    let commentElement = textArea.nextElementSibling;
    
                    if (!commentElement || !commentElement.classList.contains('check-result')) {
                        commentElement = document.createElement('span');
                        commentElement.className = 'check-result mt-2 block text-sm font-semibold';
                        textArea.insertAdjacentElement('afterend', commentElement);
                    }
    
                    if (result.comment) {
                        commentElement.style.color = result.correct ? 'green' : 'red';
                        commentElement.textContent = result.comment;
                        if (!result.correct) isAllCorrect = false;
                    } else {
                        commentElement.textContent = "Ошибка при проверке ответа.";
                        commentElement.style.color = 'black';
                        isAllCorrect = false;
                    }
                } catch (error) {
                    console.error("Ошибка при отправке запроса:", error);
                    isAllCorrect = false;
                }
            }
    
            return isAllCorrect;
        }
    
    // Генерация блока с объяснением через API
    async function generateExplanationBlock(taskBlock, isCorrect) {

        // Генерация блока объяснений
        const explanationBlock = document.createElement('div');
        explanationBlock.className = 'bg-blue-100 rounded-lg shadow-sm p-6 mb-6 explanation-block';
        explanationBlock.innerHTML = `
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Разбор задания</h3>
        <p>Генерирую...</p>
        `;

        taskBlock.insertAdjacentElement('afterend', explanationBlock);

        // Прокручиваем к объяснению
        explanationBlock.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });

        // Подготовка данных для API
        const taskTitle = taskBlock.querySelector('h2').textContent.trim();
        const testAnswers = Array.from(taskBlock.querySelectorAll('input[type="checkbox"]')).map(input => ({
            condition: input.parentElement.textContent.trim(),
            userAnswer: input.checked,
            correctAnswer: input.dataset.answer === '+'
        }));

        const textAnswers = Array.from(taskBlock.querySelectorAll('textarea')).map(textArea => ({
            userAnswer: textArea.value.trim(),
            correctAnswer: textArea.dataset.answer.trim()
        }));

        // Запрос к API для генерации объяснений
        try {
            const response = await fetch("/api/generate_explanation", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    task_title: taskTitle,
                    is_correct: isCorrect,
                    test_answers: testAnswers,
                    text_answers: textAnswers,
                }),
            });

            const result = await response.json();

            // Генерация блока объяснений
            explanationBlock.innerHTML = `
                <h3 class="text-lg font-semibold text-gray-900 mb-4">Разбор задания</h3>
                <p>${result.explanation || "Ошибка при генерации объяснения."}</p>
            `;

            // Прокручиваем к объяснению
            explanationBlock.scrollIntoView({
                behavior: "smooth",
                block: "center",
            });
        } catch (error) {
            console.error("Ошибка при запросе к API для объяснения:", error);

            const errorBlock = document.createElement('div');
            errorBlock.className = 'bg-red-100 rounded-lg shadow-sm p-6 mb-6';
            errorBlock.innerHTML = `
                <h3 class="text-lg font-semibold text-red-900 mb-4">Ошибка</h3>
                <p>Не удалось сгенерировать разбор задания. Попробуйте позже.</p>
            `;
            taskBlock.insertAdjacentElement('afterend', errorBlock);
        }
    }

    // Функция для создания нового блока theory
    async function generateBlock(question, inputBlock) {
        const contextBlock = inputBlock.closest(".bg-white");
        const context = contextBlock.querySelector(".prose")?.textContent.trim() || "";

        // Создаём новый блок
        const newBlock = document.createElement("div");
        newBlock.classList.add("bg-white", "rounded-lg", "shadow-sm", "p-6", "mb-6");
        newBlock.innerHTML = `
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Информация по блоку</h3>
            <p>Генерирую...</p>
        `;
        contextBlock.parentNode.insertBefore(newBlock, contextBlock.nextSibling);

        try {
            const response = await fetch("/api/generate_block", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question, context }),
            });

            if (response.ok) {
                const data = await response.json();
                if (data.title && data.content) {
                    // Создаём новый блок
                    newBlock.innerHTML = `
                        <h2 class="text-lg font-semibold text-gray-900 mb-4">${data.title}</h2>
                        <div class="prose max-w-none text-gray-700">
                            <p>${data.content}</p>
                        </div>
                    `;

                    // Прокручиваем к объяснению
                    newBlock.scrollIntoView({
                        behavior: "smooth",
                        block: "center",
            });
                } else {
                    alert("Ошибка при генерации блока. Проверьте ввод.");
                }
            } else {
                
                alert("Ошибка на сервере. Попробуйте позже.");
            }
        } catch (error) {
            console.error("Ошибка подключения к серверу:", error);
        }
    }

    document.addEventListener("click", event => {
        if (event.target.classList.contains("submit-question")) {
            event.preventDefault();

            const inputBlock = event.target.closest(".input-block");
            const inputField = inputBlock.querySelector("input");

            if (inputField && inputField.value.trim()) {
                const question = inputField.value.trim();
                generateBlock(question, inputBlock);
                inputField.value = ""; // Очистить поле ввода
            } else {
                alert("Пожалуйста, введите вопрос!");
            }
        }
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Enter" && event.target.closest(".input-block")) {
            event.preventDefault();

            const inputBlock = event.target.closest(".input-block");
            const inputField = inputBlock.querySelector("input");

            if (inputField && inputField.value.trim()) {
                const question = inputField.value.trim();
                generateBlock(question, inputBlock);
                inputField.value = ""; // Очистить поле ввода
            } else {
                alert("Пожалуйста, введите вопрос!");
            }
        }
    });

});