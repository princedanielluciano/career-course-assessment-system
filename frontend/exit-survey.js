const surveyForm = document.getElementById("exitSurveyForm");
const messageBox = document.getElementById("message");

function field(id) {
  return document.getElementById(id).value.trim();
}

function selectedCheckboxes(containerId) {
  return Array.from(
    document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`)
  ).map(input => input.value);
}

function lines(id) {
  return field(id)
    .split("\n")
    .map(value => value.trim())
    .filter(value => value.length > 0);
}

surveyForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const ageValue = field("age");

  const payload = {
    learner_reference_number: field("lrn"),
    school_name: field("school"),
    last_name: field("lastName"),
    first_name: field("firstName"),
    middle_name: field("middleName"),
    track: field("track"),
    grade_section: field("gradeSection"),
    age: ageValue ? Number(ageValue) : null,
    date_of_birth: field("dob"),
    home_address: field("address"),
    father_name: field("father"),
    father_occupation: field("fatherOccupation"),
    mother_name: field("mother"),
    mother_occupation: field("motherOccupation"),
    parents_present_status: field("parentsStatus"),
    strand: field("strand"),
    sex: field("sex"),
    religion: field("religion"),
    place_of_birth: field("birthplace"),
    class_adviser: field("adviser"),
    guidance_counselor: field("counselor"),
    guidance_advocate: field("guidanceAdvocate"),
    career_advocate: field("careerAdvocate"),

    learnings: selectedCheckboxes("learnings"),
    problems: selectedCheckboxes("problems"),

    planned_exit: field("plannedExit"),
    reason_for_exit: field("exitReason"),

    college_choices: lines("collegeChoices"),
    study_support: selectedCheckboxes("studySupport"),
    work_choices: lines("workChoices"),
    business_choices: lines("businessChoices"),
    tesda_choices: lines("tesdaChoices"),

    other_plans: lines("otherPlans"),
    other_plans_reasons: field("otherPlansReasons"),

    recommend_school: field("recommendSchool"),
    recommendation_reason: field("recommendationReason"),
    student_signature: field("signature")
  };

  messageBox.textContent = "Saving survey...";
  messageBox.style.color = "#1e5ab6";

  try {
    const response = await fetch("/api/exit-surveys", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (!response.ok) {
      const detail = result.detail;
      const readableError = Array.isArray(detail)
        ? detail.map(item => item.msg || "Invalid field").join("; ")
        : (detail || "Unable to save the survey.");

      throw new Error(readableError);
    }

    messageBox.textContent =
      `Survey saved successfully! Record ID: ${result.id}`;
    messageBox.style.color = "green";

    surveyForm.reset();

  } catch (error) {
    messageBox.textContent = `Error: ${error.message}`;
    messageBox.style.color = "red";
    console.error("Survey submission failed:", error);
  }
});