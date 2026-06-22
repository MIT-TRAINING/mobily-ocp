/* ============================================================
   Reusable self-check quiz engine for Module 2 visualizations.
   Usage:
     renderQuiz("quizMountId", [
       { q: "Question text?",
         options: ["A", "B", "C", "D"],
         answer: 1,                       // index of correct option
         explain: "Why B is correct..." }
     ]);
   No dependencies. Works from file:// (offline).
   ============================================================ */
function renderQuiz(mountId, questions) {
  const mount = document.getElementById(mountId);
  if (!mount) return;
  mount.classList.add("quiz");
  const state = new Array(questions.length).fill(false); // answered-correctly flags
  let answeredCount = 0;

  questions.forEach((item, qi) => {
    const qEl = document.createElement("div");
    qEl.className = "q";

    const qText = document.createElement("p");
    qText.className = "qtext";
    qText.innerHTML = `<span class="num">${qi + 1}</span>${item.q}`;
    qEl.appendChild(qText);

    const explain = document.createElement("div");
    explain.className = "explain";
    explain.innerHTML = item.explain || "";

    let locked = false;
    item.options.forEach((opt, oi) => {
      const b = document.createElement("button");
      b.className = "opt";
      b.type = "button";
      b.innerHTML = `${opt}<span class="mark"></span>`;
      b.addEventListener("click", () => {
        if (locked) return;
        locked = true;
        const correct = oi === item.answer;
        // reveal correct + chosen
        Array.from(qEl.querySelectorAll(".opt")).forEach((ob, idx) => {
          ob.disabled = true;
          if (idx === item.answer) {
            ob.classList.add("correct");
            ob.querySelector(".mark").textContent = "✓";
          }
        });
        if (!correct) {
          b.classList.add("wrong");
          b.querySelector(".mark").textContent = "✗";
        }
        explain.classList.add("show");
        if (correct) state[qi] = true;
        answeredCount++;
        updateScore();
      });
      qEl.appendChild(b);
    });

    qEl.appendChild(explain);
    mount.appendChild(qEl);
  });

  const score = document.createElement("div");
  score.className = "score";
  score.textContent = `Answer the ${questions.length} questions to see your score.`;
  mount.appendChild(score);

  function updateScore() {
    const right = state.filter(Boolean).length;
    if (answeredCount < questions.length) {
      score.textContent = `${answeredCount} / ${questions.length} answered — ${right} correct so far`;
      return;
    }
    const pct = Math.round((right / questions.length) * 100);
    let msg = "";
    if (pct === 100) msg = "🏆 Perfect! You've got this concept down.";
    else if (pct >= 60) msg = "👍 Solid — review the ones you missed.";
    else msg = "📘 Revisit the visualization above, then retry.";
    score.textContent = `Score: ${right} / ${questions.length} (${pct}%) — ${msg}`;
    score.style.background = pct === 100 ? "var(--green-bg)"
      : pct >= 60 ? "var(--amber-bg)" : "var(--red-bg)";
    score.style.color = pct === 100 ? "var(--green-ink)"
      : pct >= 60 ? "var(--amber-ink)" : "var(--red-ink)";
  }
}
