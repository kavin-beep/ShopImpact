"""Shared presentation styles; native Streamlit controls keep their semantics."""
import streamlit as st


def theme_controls():
    """Theme and animation choices remain in this browser session."""
    with st.sidebar:
        with st.expander("Theme & animation", expanded=True):
            theme = st.selectbox("Theme", ["Normal", "Day", "Night"], key="visual_theme")
            motion = st.checkbox("Animated scenery", value=True, key="scenery_motion",
                                 help="Your device's reduced-motion setting also pauses the scenery.")
            st.caption("Applies to this session, including sign-in.")
    if theme != "Normal":
        scene = "night" if theme == "Night" else "day"
        paused = "" if motion else " si-paused"
        stars = "".join(f'<i class="si-star si-star-{n}"></i>' for n in range(1, 6))
        content = stars if scene == "night" else '<i class="si-sun"></i><i class="si-cloud si-cloud-1"></i><i class="si-cloud si-cloud-2"></i>'
        st.markdown(f'<div class="si-scenery si-{scene}{paused}" aria-hidden="true">{content}</div>', unsafe_allow_html=True)


def apply_styles(high_contrast=False):
    background = "#ffffff" if high_contrast else "#F5F7F3"
    surface = "#ffffff" if high_contrast else "#FFFFFF"
    sidebar = "#F5F7F2" if high_contrast else "#EDF1E9"
    muted = "#344B42" if high_contrast else "#53665C"
    st.markdown(f"""<style>
    .stApp {{ --si-bg:{background}; --si-surface:{surface}; --si-muted:{muted};
        --si-ink:#193C32; --si-line:#D9E2D8; background:var(--si-bg); color:var(--si-ink); }}
    .stApp h1 {{font-size:clamp(1.8rem,3vw,2.6rem);font-weight:650;letter-spacing:-.045em;line-height:1.18;}}
    .stApp h2,.stApp h3 {{letter-spacing:-.025em;font-weight:600;}}
    .stApp [data-testid="stMainBlockContainer"] {{max-width:1380px;padding-top:2.8rem;padding-bottom:3rem;}}
    .stApp [data-testid="stCaptionContainer"] {{opacity:1;}}
    .stApp [data-testid="stCaptionContainer"] p {{color:var(--si-muted);line-height:1.6;}}
    .stApp [data-testid="stSidebar"] {{background:{sidebar};border-right:1px solid var(--si-line);}}
    .stApp [data-testid="stSidebar"] h1 {{font-size:1.65rem;}}
    .stApp [data-testid="stMetric"] {{background:var(--si-surface);border:1px solid var(--si-line);
        border-radius:16px;padding:20px 22px;min-height:122px;box-shadow:0 3px 12px #173b2e05;}}
    .stApp [data-testid="stMetricLabel"] p {{color:var(--si-muted);font-size:.85rem;}}
    .stApp [data-testid="stMetricValue"] {{font-size:clamp(1.4rem,2.5vw,2rem);font-weight:600;letter-spacing:-.035em;}}
    .stApp [data-testid="stForm"],.stApp [data-testid="stVerticalBlockBorderWrapper"] {{border-color:var(--si-line);border-radius:16px;}}
    .stApp [data-testid="stForm"] {{padding:24px;background:var(--si-surface);}}
    .stApp [data-testid="stExpander"] {{border-color:var(--si-line);border-radius:12px;}}
    .stApp button {{border-radius:10px;font-weight:550;}}
    .stApp button[kind="primary"],.stApp button[kind="primary"] p {{color:#fff;background:#28644F;}}
    .stApp button:focus-visible,.stApp input:focus-visible {{outline:3px solid #336FA5;outline-offset:3px;}}
    .stApp [data-baseweb="tab-list"] {{gap:20px;border-bottom:1px solid var(--si-line);}}
    .stApp [data-baseweb="tab"] {{padding:12px 0;font-size:.9rem;}}
    .stApp [data-baseweb="input"],.stApp [data-baseweb="select"] > div {{border-radius:9px;}}
    .stApp .si-hero {{padding:28px 32px;border:1px solid var(--si-line);border-radius:22px;
        background:var(--si-surface);margin-bottom:24px;border-left:5px solid #28644F;}}
    .stApp .si-hero h1 {{margin:12px 0;color:var(--si-ink);}}
    .stApp .si-hero p {{margin:0;color:var(--si-muted);line-height:1.7;max-width:740px;}}
    .stApp .si-chip {{display:inline-block;background:#E6EEDF;color:#214E3D;border-radius:24px;
        padding:6px 12px;font-size:.76rem;font-weight:600;margin:0 8px 8px 0;}}
    .stApp [data-baseweb="tab-list"] {{gap:8px;padding:6px;background:var(--si-surface);border-radius:14px;}}
    .stApp [data-baseweb="tab"] {{padding:10px 14px;border-radius:9px;height:auto;}}
    .stApp [data-baseweb="tab"][aria-selected="true"] {{background:#E6EEDF;color:#214E3D;}}
    .stApp [data-testid="stMetric"] {{border-top:3px solid #91B08B;}}
    @media(prefers-reduced-motion:no-preference) {{
        .stApp button {{transition:background-color .15s ease;}}
        .stApp .si-brand svg {{animation:si-sway 8s ease-in-out infinite;transform-origin:center;}}
        @keyframes si-sway {{0%,100% {{transform:rotate(-3deg);}} 50% {{transform:rotate(3deg);}}}}
    }}
    .stApp .si-eyebrow {{font-size:.74rem;letter-spacing:.16em;font-weight:650;color:var(--si-muted);margin-bottom:12px;}}
    .stApp .si-brand {{background:#1B4437;border-radius:24px;padding:42px;color:#F7F8F0;
        min-height:440px;position:relative;overflow:hidden;margin:0 20px 22px 0;}}
    .stApp .si-brand h2 {{color:#F7F8F0;font-size:clamp(2rem,3.2vw,3.1rem);line-height:1.12;margin:28px 0 20px;max-width:370px;}}
    .stApp .si-brand p {{color:#D4E0D1;font-size:1rem;line-height:1.7;}}
    .stApp .si-brand .si-wordmark {{color:#F7F8F0;font-size:1.15rem;font-weight:600;letter-spacing:-.02em;}}
    .stApp .si-brand .si-brand-detail {{border-top:1px solid #567363;margin-top:30px;padding-top:22px;font-size:.86rem;}}
    .stApp .si-brand svg {{position:absolute;right:20px;bottom:88px;opacity:.12;width:170px;height:170px;}}
    .stApp .si-auth-note {{font-size:.82rem;color:var(--si-muted);padding-top:12px;}}
    @media(max-width:760px) {{
        .stApp [data-testid="stMainBlockContainer"] {{padding-top:4.5rem;padding-left:1rem;padding-right:1rem;}}
        .stApp [data-testid="stHorizontalBlock"] {{row-gap:1rem;}}
        .stApp .si-brand {{min-height:0;padding:25px;margin-right:0;}}
        .stApp .si-brand h2 {{font-size:1.85rem;margin:16px 0 12px;}}
        .stApp .si-brand .si-brand-detail,.stApp .si-brand svg {{display:none;}}
        .stApp [data-testid="stMetric"] {{min-height:104px;padding:16px 18px;}}
        .stApp [data-testid="stForm"] {{padding:18px;}}
        .stApp [data-baseweb="tab-list"] {{gap:16px;}}
        .stApp .si-hero {{padding:20px;}}
    }}
    @media(max-width:1100px) {{
        .stApp [data-testid="stMainBlockContainer"] {{padding-left:1.4rem;padding-right:1.4rem;}}
        .stApp [data-testid="stMetric"] {{padding:14px 12px;}}
        .stApp [data-testid="stMetricValue"] {{font-size:1.2rem;}}
    }}
    </style>""", unsafe_allow_html=True)
    theme = st.session_state.get("visual_theme", "Normal")
    if theme == "Night" and not high_contrast:
        st.markdown("""<style>
        .stApp {--si-bg:#0B1427;--si-surface:#17243A;--si-muted:#BFCDE0;--si-ink:#EDF3FA;--si-line:#3C4E68;
            background:var(--si-bg);color:var(--si-ink);color-scheme:dark;}
        .stApp [data-testid="stSidebar"] {background:#111E32;}
        .stApp h1,.stApp h2,.stApp h3,.stApp label,.stApp p,
        .stApp [data-testid="stMetricValue"],.stApp [data-testid="stMarkdownContainer"] {color:var(--si-ink);}
        .stApp [data-testid="stHeader"] {background:#0B1427;}
        .stApp [data-baseweb="input"],.stApp [data-baseweb="input"] input,
        .stApp [data-baseweb="textarea"],.stApp textarea,.stApp [data-baseweb="select"] > div,
        .stApp [data-baseweb="base-input"],.stApp [data-testid="stNumberInput"] button {
            background:#1B2D47;color:#EDF3FA;border-color:#526681;}
        .stApp input::placeholder,.stApp textarea::placeholder {color:#BFCDE0;}
        .stApp button {background:#20334F;color:#EDF3FA;border-color:#526681;}
        .stApp button p,.stApp [data-baseweb="tab"] {color:#EDF3FA;}
        .stApp button[kind="primary"],.stApp button[kind="primary"] p {background:#28644F;color:#fff;}
        .stApp .si-chip,.stApp [data-baseweb="tab"][aria-selected="true"] {background:#284936;color:#E4F3DA;}
        .stApp [data-testid="stExpander"] {background:var(--si-surface);}
        .stApp [data-testid="stExpander"] summary {background:var(--si-surface);color:var(--si-ink);}
        .stApp [data-testid="stExpander"] summary p {color:var(--si-ink);}
        .stApp [data-testid="stAlert"] {background:#1B2D47;color:#EDF3FA;}
        .stApp [data-testid="stDataFrame"],.stApp [data-testid="stTable"] {background:#17243A;color:#EDF3FA;}
        .stApp a {color:#A8D5FF;}
        .stApp [data-testid="stCaptionContainer"] p,.stApp .si-hero p {color:var(--si-muted);}
        </style>""", unsafe_allow_html=True)
    elif theme == "Day" and not high_contrast:
        st.markdown("""<style>
        .stApp {--si-bg:#EDF7FC;--si-surface:#FFFFFF;--si-line:#CFDFE6;
            background:linear-gradient(150deg,#E2F3FF,#F6FAEE 75%);}
        .stApp [data-testid="stSidebar"] {background:#EAF3EE;}
        .stApp .si-hero {background:linear-gradient(120deg,#FFFFFF,#F2F9E7);}
        </style>""", unsafe_allow_html=True)
    # Fixed, non-interactive scenery lives behind opaque content cards.
    st.markdown("""<style>
    .si-scenery {position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:0;}
    .stApp [data-testid="stMainBlockContainer"] {position:relative;z-index:1;}
    .si-night {background-image:radial-gradient(1px 1px at 18% 15%,#CCDFFF 98%,transparent),
        radial-gradient(1px 1px at 62% 28%,#CCDFFF 98%,transparent),
        radial-gradient(1px 1px at 85% 60%,#CCDFFF 98%,transparent);background-size:270px 230px;}
    .si-star {position:absolute;width:100px;height:2px;background:linear-gradient(90deg,transparent,#DAE8FF);
        opacity:0;transform:rotate(35deg);border-radius:50%;}
    .si-star-1 {left:12%;top:8%;--delay:0s;}
    .si-star-2 {left:48%;top:16%;--delay:4s;}
    .si-star-3 {left:70%;top:4%;--delay:8s;}
    .si-star-4 {left:25%;top:35%;--delay:12s;}
    .si-star-5 {left:55%;top:48%;--delay:16s;}
    .si-sun {position:absolute;right:9%;top:10%;width:100px;height:100px;border-radius:50%;
        background:#FFE3A1;box-shadow:0 0 65px 28px #FFE3A144;opacity:.65;}
    .si-cloud {position:absolute;width:190px;height:45px;border-radius:80px;background:#FFFFFF;opacity:.45;}
    .si-cloud::before,.si-cloud::after {content:"";position:absolute;background:inherit;border-radius:50%;}
    .si-cloud::before {width:80px;height:80px;left:30px;bottom:0;}
    .si-cloud::after {width:100px;height:100px;right:25px;bottom:0;}
    .si-cloud-1 {left:8%;top:18%;}
    .si-cloud-2 {left:55%;top:64%;}
    @media(prefers-reduced-motion:no-preference) {
        .si-star {animation:si-fall 22s linear infinite;animation-delay:var(--delay);}
        .si-cloud {animation:si-drift 55s ease-in-out infinite alternate;}
        .si-cloud-2 {animation-delay:-25s;}
        .si-sun {animation:si-glow 12s ease-in-out infinite alternate;}
        @keyframes si-fall {0%,6% {opacity:0;transform:translate(0,0) rotate(35deg);}
            8% {opacity:.65;} 16% {opacity:0;transform:translate(340px,238px) rotate(35deg);} 100% {opacity:0;}}
        @keyframes si-drift {to {transform:translateX(120px);}}
        @keyframes si-glow {to {transform:scale(1.06);opacity:.85;}}
    }
    .si-paused *, .si-paused *::before,.si-paused *::after {animation:none!important;}
    @media(prefers-reduced-motion:reduce) {.si-scenery * {animation:none!important;}}
    </style>""", unsafe_allow_html=True)
    if high_contrast:
        st.markdown('<style>.si-scenery {display:none;}</style>', unsafe_allow_html=True)


def brand_panel():
    st.markdown("""<section class="si-brand">
    <div class="si-wordmark">◌ &nbsp; ShopImpact</div>
    <div class="si-chip">2026 refresh</div>
    <h2>Small choices.<br>A clearer picture.</h2>
    <p>Your shopping journal for thoughtful spending,<br>everyday habits, and a little perspective.</p>
    <svg viewBox="0 0 100 100" aria-hidden="true"><path d="M20 80C10 30 40 10 85 15C90 60 55 85 20 80Z" fill="#DCE8BA"/><path d="M18 86L72 28M38 66L37 38M52 53L72 54" stroke="#1B4437" stroke-width="4" fill="none"/></svg>
    <p class="si-brand-detail">Private purchase history &nbsp;·&nbsp; Monthly goals<br>Reference impact estimates &nbsp;·&nbsp; Practical alternatives</p>
    </section>""", unsafe_allow_html=True)
