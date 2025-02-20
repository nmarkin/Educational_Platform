// document.querySelectorAll('.check-answers').forEach(button => {
//     button.addEventListener('click', event => {
//         // Найти родительский элемент, содержащий задание (карточку)
//         const card = event.target.closest('.bg-white');
//         if (!card) return;

//         // Получить тип задания из структуры
//         const testInputs = card.querySelectorAll('input[type="checkbox"]');

//         // Если это тестовое задание
//         testInputs.forEach(input => {
//             const isChecked = input.checked; // Отмечен ли текущий ответ
//             const correctAnswer = input.dataset.answer === '+'; // Правильный ответ из data-answer

//             // Найти или создать элемент для отображения результата
//             let result = input.nextElementSibling; // Проверяем следующий элемент за input
//             if (!result || !result.classList.contains('check-result')) {
//                 result = document.createElement('span');
//                 result.className = 'check-result ml-2 text-sm font-semibold';
//                 input.parentElement.appendChild(result);
//             }

//             // Вывести результат
//             if (isChecked === correctAnswer) {
//                 result.textContent = '✔ Правильно!';
//                 result.style.color = 'green';
//             } else {
//                 result.textContent = '✘ Неправильно';
//                 result.style.color = 'red';
//             }
//         });
//     });
// });


// document.querySelectorAll('.check-answers').forEach(button => {
//     button.addEventListener('click', async event => {
//         const card = event.target.closest('.bg-white');
//         if (!card) return;

//         const textAreas = card.querySelectorAll('textarea');
//         const taskTitle = card.querySelector('h2').textContent;

//         for (const textArea of textAreas) {
//             const userAnswer = textArea.value.trim();
//             const correctAnswer = textArea.dataset.answer.trim();

//             if (!userAnswer) {
//                 alert("Пожалуйста, введите ответ перед проверкой.");
//                 continue;
//             }

//             try {
//                 const response = await fetch("/api/check_text_answer", {
//                     method: "POST",
//                     headers: {
//                         "Content-Type": "application/json",
//                     },
//                     body: JSON.stringify({
//                         user_answer: userAnswer,
//                         correct_answer: correctAnswer,
//                         task_title: taskTitle,
//                     }),
//                 });

//                 const result = await response.json();
//                 let commentElement = textArea.nextElementSibling;

//                 if (!commentElement || !commentElement.classList.contains('check-result')) {
//                     commentElement = document.createElement('span');
//                     commentElement.className = 'check-result mt-2 block text-sm font-semibold';
//                     textArea.insertAdjacentElement('afterend', commentElement);
//                 }

//                 if (result.comment) {
//                     if (result.correct){
//                         commentElement.style.color = 'green';
//                     } else {
//                         commentElement.style.color = 'red';
//                     }
//                     commentElement.textContent = result.comment;
//                 } else {
//                     commentElement.textContent = "Ошибка при проверке ответа.";
//                     commentElement.style.color = 'black';
//                 }
//             } catch (error) {
//                 console.error("Ошибка при отправке запроса:", error);
//             }
//         }
//     });
// });

    // // Обработчик для кнопки "Далее"
    // document.addEventListener("click", (event) => {
    //     if (event.target.classList.contains("next-button")) {
    //         event.preventDefault();

    //         // Показываем следующий блок
    //         const nextBlockId = event.target.getAttribute("data-next");
    //         const nextBlock = document.getElementById(nextBlockId);

            // if (nextBlock) {
            //     nextBlock.classList.remove("hidden");

            //     // Прокручиваем к следующему блоку
            //     nextBlock.scrollIntoView({
            //         behavior: "smooth", // Плавная прокрутка
            //         block: "center"    // Центрируем блок в экране
            //     });
            // } else {
            //     // Если следующий блок не найден, показываем сообщение "Глава пройдена!"
            //     const chapterCompletedMessage = document.getElementById("chapter-completed");
            //     if (chapterCompletedMessage) {
            //         chapterCompletedMessage.classList.remove("hidden");

            //         // Прокручиваем к сообщению "Глава пройдена!"
            //         chapterCompletedMessage.scrollIntoView({
            //             behavior: "smooth", // Плавная прокрутка
            //             block: "center"    // Центрируем сообщение
            //         });
            //     }
            // }

    //         // Деактивируем текущую кнопку "Далее" (опционально)
    //         event.target.disabled = true;
    //     }
    // });

    
document.querySelectorAll('.check-answers').forEach(button => {
    button.addEventListener('click', event => {
        // Найти родительский блок с классом "task-block"
        const taskBlock = event.target.closest('.task-block');
        if (!taskBlock) {
            console.error("Не удалось найти родительский блок с классом '.task-block'.");
            return;
        }

        console.log("Найден taskBlock:", taskBlock);

        // Проверка чекбоксов
        const testInputs = taskBlock.querySelectorAll('input[type="checkbox"]');
        if (testInputs.length === 0) {
            console.warn("Чекбоксы внутри taskBlock не найдены. Проверьте HTML-структуру.");
        } else {
            console.log("Найдены чекбоксы:", testInputs);
        }

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
            }
        });

        // Проверка текстового задания (textarea)
        const textAreas = taskBlock.querySelectorAll('textarea');
        textAreas.forEach(async textArea => {
            const userAnswer = textArea.value.trim();
            const correctAnswer = textArea.dataset.answer.trim();

            if (!userAnswer) {
                alert("Пожалуйста, введите ответ перед проверкой.");
                return;
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
                } else {
                    commentElement.textContent = "Ошибка при проверке ответа.";
                    commentElement.style.color = 'black';
                }
            } catch (error) {
                console.error("Ошибка при отправке запроса:", error);
            }
        });
    });
});
