document.addEventListener("DOMContentLoaded", function () {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.multiple = true;
    fileInput.style.display = "none";

    const uploadButton = document.getElementById("upload-btn");
    const uploadContainer = document.getElementById("upload-container");
    const fileList = document.getElementById("file-list");
    const previewButton = document.getElementById("preview-btn");
    const generatingDiv = document.getElementById("generating");
    const courseStructureDiv = document.getElementById("course-structure");
    const publishButton = document.getElementById("publish-btn");

    let uploadedFiles = [];
    let courseFolder = null; // Динамическая папка курса
    let courseNumber = null; // Фиксируем номер курса

    uploadButton.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", async function (event) {
        const files = event.target.files;
        if (!files.length) return;

        uploadContainer.classList.remove("hidden");

        if (courseNumber === null) {
            courseNumber = await getNextCourseNumber(); // Фиксируем номер курса при первой загрузке
        }

        for (const file of files) {
            uploadedFiles.push(file.name);
            const fileBlock = document.createElement("div");
            fileBlock.className = "flex items-center justify-between p-3 bg-gray-50 rounded-lg";
            fileBlock.innerHTML = `
                    <div class="flex items-center gap-3">
                            <i class="fas fa-file-pdf text-custom"></i>
                            <span>${file.name}</span>
                    </div>
                    <span class="text-sm text-gray-500">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
            `;
            fileList.appendChild(fileBlock);

            uploadFile(file, file.name, courseNumber);
        }
    });

    async function getNextCourseNumber() {
        const response = await fetch("/api/get_next_course_number");
        const result = await response.json();
        return result.course_number;
    }

    function uploadFile(file, fileName, courseNumber) {
        const progressBar = document.getElementById(`progress-${fileName}`);
        const formData = new FormData();
        formData.append("file", file);
        formData.append("course_number", courseNumber); // Передаем фиксированный номер курса

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);

        xhr.upload.onprogress = function (event) {
            if (event.lengthComputable) {
                const percentComplete = Math.round((event.loaded / event.total) * 100);
                progressBar.style.width = percentComplete + "%";
            }
        };

        xhr.onload = function () {
            if (xhr.status == 200) {
                progressBar.style.width = "100%";
                progressBar.classList.add("bg-green-500");
            } else {
                progressBar.style.width = "100%";
                progressBar.classList.add("bg-red-500");
            }
        };

        xhr.onerror = function () {
            progressBar.style.width = "100%";
            progressBar.classList.add("bg-red-500");
        };

        xhr.send(formData);
    }


    previewButton.addEventListener("click", async () => {
        if (courseNumber === null) {
            alert("Файлы не загружены!");
            return;
        }

        const courseName = document.querySelector("input[type='text']").value.trim();
        const courseDescription = document.querySelector("textarea").value.trim();
        const courseIntensity = document.querySelector("input[type='range']").value;

        if (!courseName) {
            alert("Введите название курса!");
            return;
        }

        generatingDiv.classList.remove("hidden");
        courseStructureDiv.classList.add("hidden");

        const requestData = {
            course_name: courseName,
            description: courseDescription,
            intensity: courseIntensity,
            files: uploadedFiles,
            course_number: courseNumber
        };

        const response = await fetch("/api/generate_contents", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();
        if (response.ok) {
            loadCourseStructure(result.course_folder);
            courseFolder = result.course_folder
        } else {
            alert("Ошибка: " + result.error);
            generatingDiv.textContent = "Ошибка при генерации оглавления.";
        }
    });

    async function loadCourseStructure(courseFolder) {
        try {
            const response = await fetch(`/static/courses/${courseFolder}/contents.json`);
            const data = await response.json();

            // Очищаем контейнер и наполняем главами
            courseStructureDiv.innerHTML = "";
            data.chapters.forEach(chapter => {
                const chapterBlock = document.createElement("div");
                chapterBlock.className = "bg-white p-4 rounded-lg border border-gray-200 hover:border-custom hover:shadow-md transition-all duration-200";
                chapterBlock.innerHTML = `
                    <div class="flex justify-between mb-3">
                        <span class="font-medium chapter-title" contenteditable="true" data-id="${chapter.id}">${chapter.title}</span>
                        <div class="relative">
                            <i class="fas fa-grip-vertical text-gray-400 cursor-pointer hover:text-gray-600" onclick="toggleMenu(${chapter.id})"></i>
                            <div id="menu-${chapter.id}" class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg hidden">
                                <ul class="py-1">
                                    <li><button onclick="mergeChapters(${chapter.id})" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Объединить</button></li>
                                    <li><button onclick="splitChapter(${chapter.id})" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Разделить</button></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div class="space-y-2">
                        <div class="flex items-center text-sm text-gray-600">${chapter.summary}</div>
                    </div>
                `;
                courseStructureDiv.appendChild(chapterBlock);
            });

            // Скрываем индикатор генерации и показываем курс
            generatingDiv.classList.add("hidden");
            courseStructureDiv.classList.remove("hidden");

            document.querySelectorAll(".chapter-title").forEach(element => {
                element.addEventListener("blur", saveTitleChange);
            });

        } catch (error) {
            console.log(error)
            generatingDiv.textContent = "Ошибка загрузки оглавления.";
        }
    }

    window.toggleMenu = function (chapterId) {
        const menu = document.getElementById(`menu-${chapterId}`);
        menu.classList.toggle("hidden");
    };

    function saveTitleChange(event) {
        const chapterId = event.target.getAttribute("data-id");
        const newTitle = event.target.textContent.trim();

        fetch("/api/update_chapter_title", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ course_folder: courseFolder, chapter_id: chapterId, new_title: newTitle })
        }).then(response => response.json())
          .then(data => console.log("Название обновлено", data))
          .catch(error => console.error("Ошибка обновления", error));
    }

    function mergeChapters(chapterId) {
        alert(`Объединение главы ${chapterId} (добавим логику)`);
    }

    function splitChapter(chapterId) {
        alert(`Разделение главы ${chapterId} (добавим логику)`);
    }

    publishButton.addEventListener("click", async () => {
        if (!courseFolder) {
            alert("Ошибка: курс не найден!");
            return;
        }

        // Блокируем кнопку и показываем процесс публикации
        publishButton.textContent = "Публикация...";
        publishButton.classList.add("bg-gray-400", "cursor-not-allowed");
        publishButton.disabled = true;

        const courseName = document.querySelector("input[type='text']").value.trim();
        const courseDescription = document.querySelector("textarea").value.trim();
        const courseIntensity = document.querySelector("input[type='range']").value;

        const requestData = {
            course_folder: courseFolder, 
            course_name: courseName,
            description: courseDescription,
            intensity: courseIntensity,
        };
        console.log(requestData)

        const response = await fetch("/api/publish_course", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ requestData })
        });

        const result = await response.json();

        if (response.ok) {
            // Перенаправляем на первую страницу курса после публикации
            window.location.href = `/course/${courseFolder}/module/1`;
        } else {
            alert("Ошибка публикации: " + result.error);
            publishButton.textContent = "Опубликовать";
            publishButton.classList.remove("bg-gray-400", "cursor-not-allowed");
            publishButton.disabled = false;
        }
    });


    document.body.appendChild(fileInput);
});
