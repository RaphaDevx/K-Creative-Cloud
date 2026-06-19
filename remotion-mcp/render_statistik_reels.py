"""
Renders all 6 Statistik topic reels — bypasses Claude Haiku API call.
Storyboards are hardcoded with HSG exam-relevant content.
"""
import json, os, sys, time, uuid, subprocess
from pathlib import Path

SHORTS_DIR = Path(__file__).parent.parent / "video-shorts-mcp"
sys.path.insert(0, str(SHORTS_DIR))
from tts_kokoro import synthesize

REMOTION_DIR = Path(__file__).parent
OUTPUT_DIR = Path.home() / "renders" / "shorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FPS = 30

SCRIPTS = {
    "statistik_t1_deskriptiv": {
        "title": "Deskriptive Statistik",
        "scenes": [
            {"headline": "DU MACHST DAS FALSCH", "subtext": "Und verlierst Punkte in der Prüfung",
             "emoji": "❌", "accent_hex": "#FF4444",
             "spoken": "Most students lose points on the very first statistics questions — not because they can't calculate, but because they forget one simple rule. Let me show you."},
            {"headline": "4 SKALENNIVEAUS", "subtext": "nominal → ordinal → intervall → verhältnis",
             "emoji": "📊", "accent_hex": "#4FC3F7",
             "spoken": "Four scale levels. Nominal: categories only, like eye color. Ordinal: ranking, like school grades. Interval: equal distances, like temperature in Celsius. Ratio: true zero, like weight or height. Each level allows different calculations."},
            {"headline": "MITTELWERT VS MEDIAN", "subtext": "Ausreisser ändern alles",
             "emoji": "⚖️", "accent_hex": "#FFD700",
             "spoken": "The mean is sensitive to outliers. One billionaire in a room of average people explodes the mean salary. The median? Completely robust. It's just the middle value. But here's the trap: always sort your data first before finding the median position."},
            {"headline": "VARIANZ: n MINUS 1", "subtext": "Bessel-Korrektur — immer!",
             "emoji": "🔢", "accent_hex": "#FF4444",
             "spoken": "Exam trap number one: the sample variance divides by n minus one, not n. Why? Because you already used the data to estimate the mean, which costs one degree of freedom. Division by n would systematically underestimate the true variance. So: n minus one. Always."},
            {"headline": "BOXPLOT LESEN", "subtext": "Median, Q1, Q3 — Schiefe sofort sichtbar",
             "emoji": "📦", "accent_hex": "#4FC3F7",
             "spoken": "The boxplot shows you five numbers: minimum, Q1, median, Q3, maximum. If the median sits closer to Q3, the distribution is left-skewed — right-heavy, long left tail. Closer to Q1 means right-skewed. Symmetrical box means symmetrical distribution."},
            {"headline": "PRÜFUNGS-CHEATSHEET", "subtext": "Diese 3 Regeln retten Punkte",
             "emoji": "🎯", "accent_hex": "#00C853",
             "spoken": "Three rules to remember: One — always sort before finding the median. Two — sample variance always uses n minus one. Three — with ordinal scale, only use median and mode, never the mean. Internalize these and you won't lose easy points."},
        ]
    },
    "statistik_t2_wahrscheinlichkeit": {
        "title": "Wahrscheinlichkeitsrechnung",
        "scenes": [
            {"headline": "WAHRSCHEINLICHKEIT: 3 AXIOME", "subtext": "Kolmogorov macht es simpel",
             "emoji": "🎲", "accent_hex": "#FF4444",
             "spoken": "Andrei Kolmogorov gave us three axioms that define all of probability. First: every probability is between zero and one. Second: the probability of the whole sample space is exactly one. Third: for mutually exclusive events, probabilities add up. That's it. Everything else follows from these three rules."},
            {"headline": "ADDITIONSSATZ", "subtext": "P(A∪B) = P(A) + P(B) − P(A∩B)",
             "emoji": "➕", "accent_hex": "#4FC3F7",
             "spoken": "The addition rule: the probability of A or B equals P of A plus P of B minus P of A and B. Why subtract? Because if you just add, you count the overlap twice. If A and B are mutually exclusive, the overlap is zero, and the formula simplifies to just addition."},
            {"headline": "BEDINGTE WAHRSCHEINLICHKEIT", "subtext": "P(A|B) = P(A∩B) / P(B)",
             "emoji": "🔍", "accent_hex": "#FFD700",
             "spoken": "Conditional probability asks: given that B already happened, how likely is A? The formula: P of A given B equals the joint probability of A and B divided by P of B. The four-field table is your best friend here — it makes every conditional probability calculation visual and fast."},
            {"headline": "SATZ VON BAYES", "subtext": "Vom Symptom zur Krankheit",
             "emoji": "🏥", "accent_hex": "#FF4444",
             "spoken": "Bayes' theorem lets you flip conditional probabilities. You know P of symptom given disease, but you want P of disease given symptom. The formula: prior probability times likelihood, divided by the total probability of the evidence. Classic exam question: a test is 99% accurate. But if the disease is rare, most positive tests are false positives."},
            {"headline": "KOMBINATORIK", "subtext": "Permutation n! vs Kombination C(n,k)",
             "emoji": "🔢", "accent_hex": "#4FC3F7",
             "spoken": "Permutations count ordered arrangements: n factorial. Combinations count unordered selections: n choose k equals n factorial divided by k factorial times n minus k factorial. The key question: does order matter? If yes, permutation. If no, combination. Exam classic: choosing a team of 5 from 20 people — order doesn't matter, so it's a combination."},
            {"headline": "UNABHÄNGIGKEIT ≠ DISJUNKTHEIT", "subtext": "Die häufigste Verwechslung",
             "emoji": "⚠️", "accent_hex": "#00C853",
             "spoken": "Critical distinction for the exam: independent means knowing A happens tells you nothing about B. Disjoint means A and B cannot both happen simultaneously. These are completely different concepts. In fact, two disjoint events with nonzero probability are always dependent — if A happens, B definitely cannot."},
        ]
    },
    "statistik_t3_verteilungen": {
        "title": "Wahrscheinlichkeitsverteilungen",
        "scenes": [
            {"headline": "DISKRET VS STETIG", "subtext": "Punktwahrscheinlichkeit nur bei diskreten!",
             "emoji": "📈", "accent_hex": "#FF4444",
             "spoken": "Discrete distributions — like Binomial or Poisson — assign probability to exact values. P of X equals 3 makes perfect sense. Continuous distributions — Normal, t, exponential — have zero probability at any single point. You can only ask for ranges. This is the most common exam trap in the distributions chapter."},
            {"headline": "BINOMIAL UND POISSON", "subtext": "B(n,p): E=np | Poi(λ): E=Var=λ",
             "emoji": "🎰", "accent_hex": "#4FC3F7",
             "spoken": "Binomial: n independent trials, each with success probability p. Expected value n times p, variance n times p times 1 minus p. Poisson: rare events per time interval with rate lambda. Both expected value and variance equal lambda. This is unique and testable — for Poisson, the standard deviation equals the square root of lambda."},
            {"headline": "NORMALVERTEILUNG & Z-TRANSFORM", "subtext": "Z = (X − μ) / σ",
             "emoji": "🔔", "accent_hex": "#FFD700",
             "spoken": "The normal distribution is symmetric around its mean, and completely described by just two parameters: mean and standard deviation. To use the standard normal table, standardize: Z equals X minus mu divided by sigma. Now P of X less than x equals phi of the z-score. Always check whether the table gives the left-tail or right-tail probability."},
            {"headline": "t, χ², F: WANN WELCHE?", "subtext": "σ unbekannt → t-Verteilung",
             "emoji": "📐", "accent_hex": "#FF4444",
             "spoken": "Three distributions for inference. The t-distribution: when sigma is unknown and you estimate it from the sample — always used in practice. The chi-squared distribution: for testing variance or goodness of fit. The F-distribution: for comparing two variances. Remember: t-distribution has heavier tails than normal, and converges to normal as sample size grows."},
            {"headline": "KOVARIANZ & KORRELATION", "subtext": "ρ = Cov(X,Y) / (σx · σy)",
             "emoji": "🔗", "accent_hex": "#4FC3F7",
             "spoken": "Covariance measures how two variables move together — positive means they rise together, negative means one rises as the other falls. But covariance depends on scale. Correlation standardizes it to the range minus one to plus one. A correlation near plus one means strong positive linear relationship. Near zero means no linear relationship — but not necessarily no relationship at all."},
            {"headline": "VERTEILUNG WÄHLEN", "subtext": "Die Entscheidungsregel",
             "emoji": "🗺️", "accent_hex": "#00C853",
             "spoken": "Quick decision tree for the exam: counting successes in n trials — Binomial. Rare events per interval — Poisson. Continuous bell-shaped — Normal. Mean when sigma is unknown — t-distribution. Variance testing — chi-squared. Comparing two variances — F-distribution. Memorize this and half the distribution questions solve themselves."},
        ]
    },
    "statistik_t4_schaetztheorie": {
        "title": "Schätztheorie & Konfidenzintervalle",
        "scenes": [
            {"headline": "DER ZENTRALE GRENZWERTSATZ", "subtext": "n ≥ 30 → X̄ ist normalverteilt",
             "emoji": "🌟", "accent_hex": "#FF4444",
             "spoken": "The Central Limit Theorem is the foundation of statistics. It says: no matter how the population is distributed, the distribution of sample means becomes approximately normal as sample size grows. The magic threshold: n greater than or equal to 30. After that, you can use z-tests even if the original data is skewed."},
            {"headline": "KI FÜR μ: ZWEI FORMELN", "subtext": "σ bekannt → z | σ unbekannt → t",
             "emoji": "📏", "accent_hex": "#4FC3F7",
             "spoken": "Confidence interval for the mean — two cases. Sigma known: x-bar plus minus z alpha-over-two times sigma over root n. Sigma unknown: x-bar plus minus t alpha-over-two times s over root n, with n minus one degrees of freedom. In practice, sigma is almost never known, so you will almost always use the t-distribution."},
            {"headline": "KI RICHTIG INTERPRETIEREN", "subtext": "Das Intervall ist zufällig — nicht μ!",
             "emoji": "🎯", "accent_hex": "#FFD700",
             "spoken": "Critical exam trap: a 95% confidence interval does NOT mean mu lies in this specific interval with 95% probability. Mu is a fixed unknown number — it either is or isn't in the interval. What 95% means: if you repeated this procedure 100 times, 95 of those intervals would contain the true mu. The interval is random, not mu."},
            {"headline": "KI FÜR ANTEILSWERT p", "subtext": "p ± z · √(p(1−p)/n)",
             "emoji": "📊", "accent_hex": "#FF4444",
             "spoken": "Confidence interval for a proportion: p-hat plus minus z times the square root of p-hat times 1 minus p-hat divided by n. This uses the normal approximation, which is valid when n times p and n times 1 minus p are both at least 5. The term under the square root is the standard error of the sample proportion."},
            {"headline": "STICHPROBENUMFANG n", "subtext": "n = (z · σ / ε)² — immer aufrunden!",
             "emoji": "🔢", "accent_hex": "#4FC3F7",
             "spoken": "How large must your sample be? For a confidence interval of width 2 epsilon: n equals z alpha-over-two times sigma divided by epsilon, all squared. Always round UP — rounding down gives you a slightly too narrow interval. If sigma is unknown, use a pilot study estimate or the conservative bound sigma equals 0.5 for proportions."},
            {"headline": "ERWARTUNGSTREU & EFFIZIENT", "subtext": "E[θ̂] = θ → unverzerrt",
             "emoji": "✅", "accent_hex": "#00C853",
             "spoken": "An estimator is unbiased if its expected value equals the true parameter. The sample mean is unbiased for mu. The sample variance with n minus one is unbiased for sigma squared — with n it would be biased. Efficient means smallest variance among all unbiased estimators. The OLS estimator in regression is both — that's the Gauss-Markov theorem."},
        ]
    },
    "statistik_t5_hypothesentests": {
        "title": "Hypothesentests",
        "scenes": [
            {"headline": "DAS TESTSCHEMA IN 6 SCHRITTEN", "subtext": "Immer gleich — auswendig lernen!",
             "emoji": "📋", "accent_hex": "#FF4444",
             "spoken": "Every hypothesis test follows the same six steps. One: state H-zero and H-one. Two: set significance level alpha. Three: calculate the test statistic. Four: find the critical value from the table. Five: decision rule — reject H-zero if the test statistic exceeds the critical value. Six: interpret in context. Internalize this schema and apply it to every test type."},
            {"headline": "α-FEHLER VS β-FEHLER", "subtext": "Typ I vs Typ II — nie verwechseln!",
             "emoji": "⚠️", "accent_hex": "#4FC3F7",
             "spoken": "Alpha error — Type I: H-zero is true but you reject it. False alarm. You control this directly by choosing alpha. Beta error — Type II: H-zero is false but you fail to reject it. Missed effect. Power equals one minus beta — the probability of correctly detecting a real effect. The tricky part: reducing alpha increases beta. You cannot minimize both simultaneously."},
            {"headline": "z-TEST UND t-TEST", "subtext": "σ bekannt → z | σ unbekannt → t",
             "emoji": "🧮", "accent_hex": "#FFD700",
             "spoken": "The z-test: test statistic is x-bar minus mu-zero divided by sigma over root n. Use only when sigma is known. The t-test: replace sigma with s, and use t-distribution with n minus one degrees of freedom. The p-value is the probability of observing a test statistic at least as extreme as yours, assuming H-zero is true. If p is less than alpha, reject."},
            {"headline": "ZWEISEITIG VS EINSEITIG", "subtext": "α/2 vs α — der kritische Unterschied",
             "emoji": "↔️", "accent_hex": "#FF4444",
             "spoken": "Two-sided test: you reject if the statistic is too large OR too small. Use alpha divided by two for each tail. Critical value z of alpha-over-two — for alpha 0.05, that's 1.96. One-sided test: reject only in one direction. Use the full alpha. Critical value z of alpha — for alpha 0.05, that's 1.645. Getting this wrong flips your answer completely."},
            {"headline": "WELCH VS POOLED", "subtext": "Erst F-Test! Dann entscheiden.",
             "emoji": "🔄", "accent_hex": "#4FC3F7",
             "spoken": "Two-sample t-test: two versions. Pooled: assumes equal variances, uses a combined variance estimate. Welch: does not assume equal variances. Which one? First run the F-test for variance equality. If you reject H-zero of equal variances — use Welch. If you cannot reject — use Pooled. This decision tree is a guaranteed exam question."},
            {"headline": "p-WERT RICHTIG VERSTEHEN", "subtext": "Nicht P(H₀ ist wahr)!",
             "emoji": "🎯", "accent_hex": "#00C853",
             "spoken": "The p-value is the probability of getting a test statistic as extreme as yours, assuming H-zero is true. It is NOT the probability that H-zero is true. A small p-value means: this data would be very unlikely if H-zero were true, so we have evidence against it. A large p-value means: we cannot reject H-zero — but this does not prove H-zero is true."},
        ]
    },
    "statistik_t6_anova_regression": {
        "title": "ANOVA & Lineare Regression",
        "scenes": [
            {"headline": "ANOVA: WARUM NICHT t-TEST?", "subtext": "α-Kumulierung verhindert",
             "emoji": "🚫", "accent_hex": "#FF4444",
             "spoken": "Why not run multiple t-tests to compare three or more groups? Because each test has a 5% chance of error. With ten pairwise tests, your overall error rate explodes to over 40%. ANOVA solves this by testing all groups simultaneously in one F-test, keeping alpha at exactly 5%. That's its entire purpose."},
            {"headline": "SST = SSB + SSW", "subtext": "Gesamtvariation = zwischen + innerhalb",
             "emoji": "📊", "accent_hex": "#4FC3F7",
             "spoken": "ANOVA decomposes total variation. SST is total variation around the grand mean. SSB — between groups — measures how far group means deviate from the grand mean: the systematic effect. SSW — within groups — measures random variation inside each group: the error. The F-statistic equals mean square between divided by mean square within. Large F means groups differ significantly."},
            {"headline": "REGRESSION: β₁ UND β₀", "subtext": "KQ-Schätzung minimiert Σ(y−ŷ)²",
             "emoji": "📉", "accent_hex": "#FFD700",
             "spoken": "Simple linear regression: y-hat equals beta-zero plus beta-one times x. Beta-one, the slope, equals covariance of X and Y divided by variance of X. Beta-zero, the intercept, equals y-bar minus beta-one times x-bar. The OLS method finds these values by minimizing the sum of squared residuals. The regression line always passes through the point x-bar, y-bar."},
            {"headline": "R² — NUR EIN TEIL", "subtext": "R² = SSR/SST, aber allein ungenügend",
             "emoji": "📐", "accent_hex": "#FF4444",
             "spoken": "R-squared tells you what fraction of total variation in Y is explained by X. An R-squared of 0.7 means 70% explained. But R-squared alone is not enough. Adding more variables always increases R-squared even if they're useless. Use adjusted R-squared for multiple regression — it penalizes for unnecessary variables. And always check residual plots for patterns."},
            {"headline": "GAUSS-MARKOV THEOREM", "subtext": "OLS ist BLUE — beste lineare Schätzung",
             "emoji": "🏆", "accent_hex": "#4FC3F7",
             "spoken": "The Gauss-Markov theorem guarantees that the OLS estimator is BLUE: Best Linear Unbiased Estimator. Among all linear unbiased estimators, OLS has the smallest variance. But the theorem requires four conditions: linearity, random sampling, no perfect multicollinearity, and zero conditional mean of errors. Violation of any condition can invalidate OLS estimates."},
            {"headline": "DUMMY-VARIABLEN & INTERAKTION", "subtext": "FRAU=1 → andere Gerade für Frauen",
             "emoji": "🔀", "accent_hex": "#00C853",
             "spoken": "Dummy variables allow categorical variables in regression. Gender dummy: 1 for female, 0 for male. Just adding the dummy shifts the intercept — same slope for both groups. Adding an interaction term — dummy times continuous variable — allows different slopes. For women: intercept is beta-one plus delta-one, slope is beta-two plus delta-two. The dummy changes everything about the regression line."},
        ]
    },
}


def render_topic(key, script_data):
    t_start = time.time()
    render_id = uuid.uuid4().hex[:8]
    PUBLIC_AUDIO = REMOTION_DIR / "public" / "audio" / render_id
    PUBLIC_AUDIO.mkdir(parents=True, exist_ok=True)

    scenes = script_data["scenes"]
    title = script_data["title"]

    print(f"\n{'='*60}")
    print(f"Rendering: {title}")
    print(f"{'='*60}")

    # TTS per scene
    print(f"[1/3] TTS (am_adam)...")
    total_frames = 0
    for i, scene in enumerate(scenes):
        audio_path = str(PUBLIC_AUDIO / f"scene_{i:03d}.wav")
        duration = synthesize(scene["spoken"], audio_path, voice="am_adam", speed=1.2)
        duration_frames = int(duration * FPS) + 6
        scene["audioFile"] = f"{render_id}/scene_{i:03d}.wav"
        scene["durationFrames"] = duration_frames
        total_frames += duration_frames
        print(f"      Scene {i}: {duration:.1f}s — {scene['headline']}")

    print(f"      Total: {total_frames} frames = {total_frames/FPS:.1f}s")

    # Build props
    video_props = {"scenes": scenes, "title": title, "totalDurationFrames": total_frames}
    props_path = REMOTION_DIR / "public" / "video-props.json"
    props_path.write_text(json.dumps(video_props, indent=2))

    # Remotion render
    output_path = str(OUTPUT_DIR / f"{key}.mp4")
    print(f"[2/3] Remotion render → {output_path}")

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "VideoShort", output_path,
        "--props", json.dumps(video_props),
        "--duration-in-frames", str(total_frames),
        "--fps", str(FPS),
        "--width", "1080", "--height", "1920",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION_DIR))
    if result.returncode != 0:
        print("ERROR:", result.stderr[-1500:])
        return {"error": result.stderr[-500:], "key": key}

    elapsed = time.time() - t_start
    print(f"[3/3] Done in {elapsed:.0f}s → {output_path}")
    return {"output": output_path, "title": title, "scenes": len(scenes),
            "duration_s": round(total_frames / FPS, 1), "render_time_s": round(elapsed, 1)}


if __name__ == "__main__":
    results = []
    for key, data in SCRIPTS.items():
        result = render_topic(key, data)
        results.append(result)
        print(json.dumps(result, indent=2))

    print("\n\nSUMMARY:")
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['key']}: {r['error'][:80]}")
        else:
            print(f"  ✅ {r['title']}: {r['duration_s']}s → {r['output']}")
