import streamlit as st

# Apply custom CSS for compact spacing
def apply_custom_css():
    st.markdown("""
        <style>
        /* Reduce padding in main block container */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        
        /* Reduce space between elements */
        .element-container {
            margin-bottom: 0.5rem;
        }
        
        /* Reduce space between widgets */
        .stButton, .stTextInput, .stSelectbox, .stTextArea {
            margin-bottom: 0.5rem;
        }
        
        /* Tighten up forms */
        .stForm {
            padding: 0.5rem;
            border: 1px solid #e0e0e0;
            border-radius: 0.5rem;
        }
        
        /* Reduce form submit button spacing */
        .stForm > div:last-child {
            margin-top: 0.5rem;
        }
        
        /* Mobile-specific adjustments */
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.5rem;
                padding-bottom: 0.5rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            
            .element-container {
                margin-bottom: 0.3rem;
            }
            
            /* Reduce header sizes on mobile */
            h1 {
                font-size: 1.8rem;
            }
            h2 {
                font-size: 1.4rem;
            }
            h3 {
                font-size: 1.2rem;
            }
        }
        
        /* Reduce header spacing */
        h1, h2, h3 {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        /* Tighten sidebar */
        section[data-testid="stSidebar"] {
            padding-top: 1rem;
        }
        
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem;
        }
        
        /* Reduce tab spacing */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 0.5rem;
        }
        
        /* Compact expander */
        .streamlit-expanderHeader {
            padding: 0.5rem;
        }
        
        .streamlit-expanderContent {
            padding: 0.5rem;
        }
        
        /* Reduce divider spacing */
        hr {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

