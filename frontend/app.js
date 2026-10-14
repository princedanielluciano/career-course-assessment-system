const API = "";

const pageTitles = {
    dashboard: "Dashboard",
    students: "Student Records",
    assessment: "Student Assessment",
    questions: "Assessment Questions",
    courses: "College Courses",
    schools: "Schools and Colleges",
    results: "Assessment Results"
};

let questionsCache = [];
let studentsCache = [];

async function apiRequest(path, options = {}) {
    const response = await fetch(API + path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const text = await response.text();
    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = { detail: text };
    }

    if (!response.ok) {
        const message = data.detail || `Request failed: ${response.status}`;
        throw new Error(
            typeof message === "string" ? message : JSON.stringify(message)
        );
    }

    return data;
}

function showNotice(message, type = "success") {
    const notice = document.getElementById("notice");
    notice.textContent = message;
    notice.className = `notice ${type}`;

    window.scrollTo({ top: 0, behavior: "smooth" });

    window.setTimeout(() => {
        notice.classList.add("hidden");
    }, 5000);
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}

function showPage(pageName) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.add("hidden");
    });

    const selectedPage = document.getElementById(`page-${pageName}`);
    if (selectedPage) selectedPage.classList.remove("hidden");

    document.querySelectorAll(".nav-link").forEach(button => {
        button.classList.toggle("active", button.dataset.page === pageName);
    });

    document.getElementById("page-title").textContent =
        pageTitles[pageName] || "CareerPath";

    if (pageName === "dashboard") loadDashboard();
    if (pageName === "students") loadStudents();
    if (pageName === "assessment") loadAssessmentPage();
    if (pageName === "questions") loadQuestions();
    if (pageName === "courses") loadCourses();
    if (pageName === "schools") loadSchools();
    if (pageName === "results") loadResults();
}

document.querySelectorAll("[data-page]").forEach(button => {
    button.addEventListener("click", () => showPage(button.dataset.page));
});

document.querySelectorAll("[data-goto]").forEach(button => {
    button.addEventListener("click", () => showPage(button.dataset.goto));
});

async function loadDashboard() {
    try {
        const [students, questions, courses, results] = await Promise.all([
            apiRequest("/api/students"),
            apiRequest("/api/questions"),
            apiRequest("/api/programs"),
            apiRequest("/api/assessments")
        ]);

        document.getElementById("stat-students").textContent = students.length;
        document.getElementById("stat-questions").textContent = questions.length;
        document.getElementById("stat-courses").textContent = courses.length;
        document.getElementById("stat-assessments").textContent = results.length;
    } catch (error) {
        showNotice(`Could not load dashboard: ${error.message}`, "error");
    }
}

async function loadStudents() {
    try {
        studentsCache = await apiRequest("/api/students");

        document.getElementById("students-count").textContent =
            `${studentsCache.length} student record(s)`;

        const tbody = document.getElementById("students-table");

        tbody.innerHTML = studentsCache.length
            ? studentsCache.map(student => `
                <tr>
                    <td>${student.id}</td>
                    <td>${escapeHTML(student.full_name)}</td>
                    <td>${escapeHTML(student.email || "—")}</td>
                    <td>${escapeHTML(student.grade_level)}</td>
                    <td>${escapeHTML(student.strand || "—")}</td>
                </tr>
            `).join("")
            : `<tr><td colspan="5">No students found. Add a student above.</td></tr>`;

        const select = document.getElementById("assessment-student");
        const previousValue = select.value;

        select.innerHTML = `<option value="">Choose a registered student</option>` +
            studentsCache.map(student => `
                <option value="${student.id}">
                    ${escapeHTML(student.full_name)} (ID: ${student.id})
                </option>
            `).join("");

        if (studentsCache.some(student => String(student.id) === previousValue)) {
            select.value = previousValue;
        }
    } catch (error) {
        showNotice(`Could not load students: ${error.message}`, "error");
    }
}

document.getElementById("student-form").addEventListener("submit", async event => {
    event.preventDefault();

    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());

    values.email = values.email.trim() || null;
    values.strand = values.strand || null;

    try {
        await apiRequest("/api/students", {
            method: "POST",
            body: JSON.stringify(values)
        });

        form.reset();
        form.elements.grade_level.value = "Grade 12";
        showNotice("Student added successfully.");
        await loadStudents();
        await loadDashboard();
    } catch (error) {
        showNotice(`Unable to add student: ${error.message}`, "error");
    }
});

async function loadQuestions() {
    try {
        questionsCache = await apiRequest("/api/questions");

        const container = document.getElementById("questions-list");

        container.innerHTML = questionsCache.length
            ? questionsCache.map(question => `
                <article class="record-item">
                    <h3>${escapeHTML(question.question_text)}</h3>
                    <span class="tag">${escapeHTML(question.category)}</span>
                    <p>A. ${escapeHTML(question.option_a)}</p>
                    <p>B. ${escapeHTML(question.option_b)}</p>
                    ${question.option_c ? `<p>C. ${escapeHTML(question.option_c)}</p>` : ""}
                    ${question.option_d ? `<p>D. ${escapeHTML(question.option_d)}</p>` : ""}
                    <p class="muted">Question ID: ${question.id}</p>
                </article>
            `).join("")
            : `<p class="muted">No questions found. Add a question above.</p>`;

        renderAssessmentQuestions();
    } catch (error) {
        showNotice(`Could not load questions: ${error.message}`, "error");
    }
}

document.getElementById("question-form").addEventListener("submit", async event => {
    event.preventDefault();

    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());

    const question = {
        question_text: values.question_text.trim(),
        category: values.category.trim(),
        option_a: values.option_a.trim(),
        option_b: values.option_b.trim(),
        option_c: values.option_c.trim() || null,
        option_d: values.option_d.trim() || null,
        is_active: true
    };

    try {
        const created = await apiRequest("/api/questions", {
            method: "POST",
            body: JSON.stringify(question)
        });

        const rules = [
            ["A", values.score_a],
            ["B", values.score_b],
            ["C", values.score_c],
            ["D", values.score_d]
        ];

        for (const [option_code, interest_category] of rules) {
            const optionExists = {
                A: question.option_a,
                B: question.option_b,
                C: question.option_c,
                D: question.option_d
            }[option_code];

            if (!optionExists) continue;

            await apiRequest("/api/question-option-scores", {
                method: "POST",
                body: JSON.stringify({
                    question_id: created.id,
                    option_code,
                    interest_category: interest_category.trim(),
                    points: 1
                })
            });
        }

        form.reset();
        form.elements.category.value = "Interest";
        form.elements.score_a.value = "Technology";
        form.elements.score_b.value = "Education";
        form.elements.score_c.value = "Arts and Design";
        form.elements.score_d.value = "Business and Management";

        showNotice("Question and scoring rules saved.");
        await loadQuestions();
        await loadDashboard();
    } catch (error) {
        showNotice(
            `Question saving was not fully completed: ${error.message}. Check the Question Bank and scoring rules before trying again.`,
            "error"
        );
    }
});

async function loadAssessmentPage() {
    await loadStudents();
    await loadQuestions();
    renderAssessmentQuestions();
}

function renderAssessmentQuestions() {
    const container = document.getElementById("assessment-questions");

    if (!questionsCache.length) {
        container.innerHTML = `<p class="muted">No active questions are available. Add questions and scoring rules first.</p>`;
        return;
    }

    container.innerHTML = questionsCache.map((question, index) => {
        const options = [
            ["A", question.option_a],
            ["B", question.option_b],
            ["C", question.option_c],
            ["D", question.option_d]
        ].filter(([, value]) => value);

        return `
            <article class="question-card">
                <h3>${index + 1}. ${escapeHTML(question.question_text)}</h3>
                <p class="muted">Category: ${escapeHTML(question.category)}</p>
                ${options.map(([code, text]) => `
                    <label class="answer-option">
                        <input type="radio"
                            name="question_${question.id}"
                            value="${code}"
                            required>
                        <span>${code}. ${escapeHTML(text)}</span>
                    </label>
                `).join("")}
            </article>
        `;
    }).join("");
}

document.getElementById("assessment-form").addEventListener("submit", async event => {
    event.preventDefault();

    const studentId = Number(document.getElementById("assessment-student").value);
    if (!studentId) {
        showNotice("Please select a student first.", "error");
        return;
    }

    if (!questionsCache.length) {
        showNotice("Add assessment questions before starting.", "error");
        return;
    }

    const answers = [];

    for (const question of questionsCache) {
        const selected = document.querySelector(
            `input[name="question_${question.id}"]:checked`
        );

        if (!selected) {
            showNotice("Please answer every question before submitting.", "error");
            return;
        }

        answers.push({
            student_id: studentId,
            question_id: question.id,
            selected_option: selected.value
        });
    }

    const submitButton = event.currentTarget.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";

    try {
        for (const answer of answers) {
            await apiRequest("/api/answers", {
                method: "POST",
                body: JSON.stringify(answer)
            });
        }

        const result = await apiRequest("/api/assessments", {
            method: "POST",
            body: JSON.stringify({ student_id: studentId })
        });

        const summary = result.result_summary || {};
        const output = document.getElementById("assessment-output");

        output.innerHTML = `
            <h3>Assessment Completed</h3>
            <p><strong>Student:</strong> ${escapeHTML(summary.student_name || "Student")}</p>
            <p><strong>Strongest recorded interest:</strong> ${escapeHTML(summary.strongest_interest || "Not available")}</p>
            <p><strong>Suggested course:</strong> ${escapeHTML(summary.recommended_course || "No matching course found")}</p>
            <p><strong>Matching score:</strong> ${escapeHTML(result.matching_score ?? 0)}%</p>
            <p><strong>Answered questions:</strong> ${escapeHTML(summary.answered_questions ?? answers.length)}</p>
            <p>${escapeHTML(summary.recommendation_note || "Review this result with guidance personnel.")}</p>
            <p class="muted">This is a decision-support suggestion based on configured scoring rules, not a guaranteed prediction of academic success.</p>
        `;

        output.classList.remove("hidden");
        showNotice("Assessment submitted and result generated.");
        await loadResults();
        await loadDashboard();
    } catch (error) {
        showNotice(
            `Assessment was not completed: ${error.message}. If this student already answered a question, use a new test student or add new questions instead of deleting database records.`,
            "error"
        );
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Submit Assessment";
    }
});

async function loadCourses() {
    try {
        const courses = await apiRequest("/api/programs");
        const container = document.getElementById("courses-list");

        container.innerHTML = courses.length
            ? courses.map(course => `
                <article class="tile-card">
                    <span class="tag">${escapeHTML(course.duration_years || "—")} year(s)</span>
                    <h3>${escapeHTML(course.program_name)}</h3>
                    <p>${escapeHTML(course.description || "No description added.")}</p>
                    <p><strong>Skills:</strong> ${escapeHTML(course.skills_required || "Not specified")}</p>
                    <p><strong>Career opportunities:</strong> ${escapeHTML(course.career_opportunities || "Not specified")}</p>
                    <p class="muted">Program ID: ${course.id}</p>
                </article>
            `).join("")
            : `<p class="muted">No course records yet. Add programs using the form above.</p>`;
    } catch (error) {
        showNotice(`Could not load courses: ${error.message}`, "error");
    }
}

document.getElementById("course-form").addEventListener("submit", async event => {
    event.preventDefault();

    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());

    const course = {
        program_name: values.program_name.trim(),
        duration_years: values.duration_years ? Number(values.duration_years) : null,
        description: values.description.trim() || null,
        skills_required: values.skills_required.trim() || null,
        career_opportunities: values.career_opportunities.trim() || null
    };

    try {
        await apiRequest("/api/programs", {
            method: "POST",
            body: JSON.stringify(course)
        });

        form.reset();
        form.elements.duration_years.value = "4";
        showNotice("College course added successfully.");
        await loadCourses();
        await loadDashboard();
    } catch (error) {
        showNotice(`Unable to add course: ${error.message}`, "error");
    }
});

async function loadSchools() {
    try {
        const schools = await apiRequest("/api/schools");
        const container = document.getElementById("schools-list");

        container.innerHTML = schools.length
            ? schools.map(school => `
                <article class="tile-card">
                    <h3>${escapeHTML(school.school_name)}</h3>
                    <p><strong>Location:</strong> ${escapeHTML(school.location || "Not specified")}</p>
                    <p><strong>Website:</strong> ${school.website
                        ? `<a href="${escapeHTML(school.website)}" target="_blank" rel="noopener noreferrer">${escapeHTML(school.website)}</a>`
                        : "Not specified"}</p>
                    <p><strong>Contact:</strong> ${escapeHTML(school.contact_details || "Not specified")}</p>
                </article>
            `).join("")
            : `<p class="muted">No schools recorded yet. Add a school above.</p>`;
    } catch (error) {
        showNotice(`Could not load schools: ${error.message}`, "error");
    }
}

document.getElementById("school-form").addEventListener("submit", async event => {
    event.preventDefault();

    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());

    const school = {
        school_name: values.school_name.trim(),
        location: values.location.trim() || null,
        website: values.website.trim() || null,
        contact_details: values.contact_details.trim() || null
    };

    try {
        await apiRequest("/api/schools", {
            method: "POST",
            body: JSON.stringify(school)
        });

        form.reset();
        showNotice("School added successfully.");
        await loadSchools();
    } catch (error) {
        showNotice(`Unable to add school: ${error.message}`, "error");
    }
});

async function loadResults() {
    try {
        const results = await apiRequest("/api/assessments");
        const tbody = document.getElementById("results-table");

        tbody.innerHTML = results.length
            ? results.map(result => {
                const summary = result.result_summary || {};
                return `
                    <tr>
                        <td>${result.id}</td>
                        <td>${escapeHTML(summary.student_name || `Student #${result.student_id}`)}</td>
                        <td>${escapeHTML(summary.strongest_interest || "—")}</td>
                        <td>${escapeHTML(summary.recommended_course || "No match")}</td>
                        <td>${escapeHTML(result.matching_score ?? 0)}%</td>
                        <td>${escapeHTML(result.created_at || "—")}</td>
                    </tr>
                `;
            }).join("")
            : `<tr><td colspan="6">No assessment results yet.</td></tr>`;
    } catch (error) {
        showNotice(`Could not load results: ${error.message}`, "error");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
});