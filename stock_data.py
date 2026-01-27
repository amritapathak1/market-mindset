# Stock data for 7 different tasks
# Each task has 2 stocks with different characteristics

TASKS_DATA = [
    {
        "task_id": 1,
        "stocks": [
            {
                "name": "TechCorp Inc.",
                "ticker": "TECH",
                "image": "https://via.placeholder.com/150?text=TECH",
                "past_week_percent": 5.2,
                "short_description": "Leading technology company specializing in cloud computing and AI solutions.",
                "detailed_description": "TechCorp Inc. is a multinational technology company that focuses on cloud infrastructure, artificial intelligence, and enterprise software solutions. Founded in 2010, the company has shown consistent growth with strong quarterly earnings. Recent product launches in the AI space have positioned them as a market leader. The company has a strong balance sheet with low debt and high cash reserves. Analysts predict continued growth due to increasing demand for cloud services."
            },
            {
                "name": "GreenEnergy Co.",
                "ticker": "GREN",
                "image": "https://via.placeholder.com/150?text=GREN",
                "past_week_percent": -2.1,
                "short_description": "Renewable energy company with focus on solar and wind power generation.",
                "detailed_description": "GreenEnergy Co. is a leading renewable energy provider operating solar and wind farms across North America. Despite the recent week's decline, the company has strong long-term prospects driven by government incentives and growing environmental awareness. They recently secured major contracts with utility companies. However, short-term volatility is expected due to regulatory changes and commodity price fluctuations. The company is investing heavily in next-generation battery storage technology."
            }
        ]
    },
    {
        "task_id": 2,
        "stocks": [
            {
                "name": "HealthPlus Systems",
                "ticker": "HLTH",
                "image": "https://via.placeholder.com/150?text=HLTH",
                "past_week_percent": 3.8,
                "short_description": "Healthcare technology company providing telemedicine and digital health solutions.",
                "detailed_description": "HealthPlus Systems has revolutionized telemedicine with its innovative platform connecting patients with healthcare providers. The company experienced accelerated growth during the pandemic and has maintained strong user engagement. They recently received FDA approval for their AI-powered diagnostic tools. The company has partnerships with major insurance providers, ensuring steady revenue streams. Market analysts are optimistic about their expansion into mental health services and remote patient monitoring."
            },
            {
                "name": "RetailMax Group",
                "ticker": "RMAX",
                "image": "https://via.placeholder.com/150?text=RMAX",
                "past_week_percent": -4.5,
                "short_description": "Large retail chain adapting to e-commerce with omnichannel strategy.",
                "detailed_description": "RetailMax Group operates over 500 stores nationwide and has been investing heavily in e-commerce infrastructure. The recent week's decline reflects investor concerns about rising operational costs and competition from online retailers. However, the company's omnichannel strategy has shown promising early results. They've launched same-day delivery services in major cities and integrated AR shopping experiences. The company has a loyal customer base and strong brand recognition, though margins remain under pressure."
            }
        ]
    },
    {
        "task_id": 3,
        "stocks": [
            {
                "name": "FinTech Solutions",
                "ticker": "FINT",
                "image": "https://via.placeholder.com/150?text=FINT",
                "past_week_percent": 7.3,
                "short_description": "Digital payment processing and mobile banking platform provider.",
                "detailed_description": "FinTech Solutions has become a dominant player in digital payments and mobile banking. The company processes billions of transactions monthly and has expanded into cryptocurrency services. Recent partnerships with major retailers have boosted transaction volumes. The company benefits from the shift away from cash and traditional banking. However, regulatory scrutiny in the fintech space poses potential risks. Strong network effects and high customer switching costs provide competitive advantages."
            },
            {
                "name": "AutoDrive Motors",
                "ticker": "AUTO",
                "image": "https://via.placeholder.com/150?text=AUTO",
                "past_week_percent": -1.8,
                "short_description": "Electric vehicle manufacturer with autonomous driving technology.",
                "detailed_description": "AutoDrive Motors is an innovative electric vehicle manufacturer developing autonomous driving capabilities. The company has delivered impressive vehicle production numbers but faces intense competition in the EV market. Recent safety concerns with their autonomous features led to this week's stock decline. However, they have a strong order backlog and are expanding manufacturing capacity. The company's battery technology offers longer range than competitors. Long-term growth depends on successful deployment of self-driving features and regulatory approvals."
            }
        ]
    },
    {
        "task_id": 4,
        "stocks": [
            {
                "name": "BioPharm Industries",
                "ticker": "BIOP",
                "image": "https://via.placeholder.com/150?text=BIOP",
                "past_week_percent": 12.5,
                "short_description": "Biotechnology company developing innovative cancer treatments.",
                "detailed_description": "BioPharm Industries specializes in oncology treatments with several promising drugs in late-stage clinical trials. This week's surge followed positive Phase III trial results for their flagship cancer treatment. The company has a robust pipeline with potential blockbuster drugs. Partnership agreements with larger pharmaceutical companies provide financial stability. However, the biotech sector is inherently risky due to regulatory uncertainties and clinical trial outcomes. If approved, their lead drug could generate billions in annual revenue."
            },
            {
                "name": "Global Logistics",
                "ticker": "GLOG",
                "image": "https://via.placeholder.com/150?text=GLOG",
                "past_week_percent": 1.2,
                "short_description": "International shipping and logistics company with global operations.",
                "detailed_description": "Global Logistics operates one of the world's largest shipping fleets and logistics networks. The company has shown steady but unspectacular growth. They benefit from global trade expansion but face challenges from fuel costs and port congestion. Recent investments in automation and route optimization are improving margins. The company pays consistent dividends, making it attractive for income-focused investors. Geopolitical tensions and trade disputes present ongoing risks to international shipping operations."
            }
        ]
    },
    {
        "task_id": 5,
        "stocks": [
            {
                "name": "CyberShield Security",
                "ticker": "CYBER",
                "image": "https://via.placeholder.com/150?text=CYBER",
                "past_week_percent": 6.7,
                "short_description": "Cybersecurity software and services provider for enterprises.",
                "detailed_description": "CyberShield Security provides comprehensive cybersecurity solutions to Fortune 500 companies. Growing cyber threats have driven increased demand for their services. The company has a subscription-based model ensuring predictable recurring revenue. Recent high-profile data breaches at competing firms have highlighted the importance of robust security. They're expanding into cloud security and threat intelligence. The cybersecurity market is expected to grow significantly, positioning CyberShield favorably. Competition is intense, but their reputation and client relationships provide advantages."
            },
            {
                "name": "FoodChain Markets",
                "ticker": "FOOD",
                "image": "https://via.placeholder.com/150?text=FOOD",
                "past_week_percent": -3.2,
                "short_description": "Organic and specialty food retailer with premium market positioning.",
                "detailed_description": "FoodChain Markets operates premium grocery stores focusing on organic and locally-sourced products. The recent decline reflects broader concerns about consumer spending in a potential economic slowdown. However, the company has a dedicated customer base willing to pay premium prices. They've successfully launched meal kit services and expanded private label offerings. Real estate costs and competition from conventional grocers entering the organic space pose challenges. The company maintains strong same-store sales growth despite overall market headwinds."
            }
        ]
    },
    {
        "task_id": 6,
        "stocks": [
            {
                "name": "AeroSpace Dynamics",
                "ticker": "AERO",
                "image": "https://via.placeholder.com/150?text=AERO",
                "past_week_percent": 4.1,
                "short_description": "Aerospace and defense contractor with government and commercial contracts.",
                "detailed_description": "AeroSpace Dynamics designs and manufactures aircraft components and defense systems. The company has a diverse portfolio of government contracts providing stable revenue. Recent wins in military modernization programs boosted investor confidence. They're also expanding into commercial space ventures and urban air mobility. Long development cycles and government budget uncertainties create timing risks. The company has strong engineering capabilities and benefits from high barriers to entry in aerospace. Dividend payments have been consistent for decades."
            },
            {
                "name": "MediaStream Networks",
                "ticker": "MDIA",
                "image": "https://via.placeholder.com/150?text=MDIA",
                "past_week_percent": -5.8,
                "short_description": "Streaming entertainment platform with original content production.",
                "detailed_description": "MediaStream Networks operates a popular streaming service with millions of subscribers globally. This week's decline came after disappointing subscriber growth numbers. The company is investing heavily in original content to differentiate from competitors. They face intense competition in the crowded streaming market with pricing pressure. International expansion offers growth opportunities, though content costs remain high. The company is exploring ad-supported tiers to boost revenue. Success depends on maintaining subscriber growth while managing content spending."
            }
        ]
    },
    {
        "task_id": 7,
        "stocks": [
            {
                "name": "SmartHome Tech",
                "ticker": "SMRT",
                "image": "https://via.placeholder.com/150?text=SMRT",
                "past_week_percent": 8.9,
                "short_description": "IoT and smart home device manufacturer with ecosystem approach.",
                "detailed_description": "SmartHome Tech manufactures connected home devices including smart thermostats, security cameras, and lighting systems. The company has built a comprehensive ecosystem encouraging customers to buy multiple products. Strong brand loyalty and positive reviews drive sales growth. They recently announced integration with major voice assistants. Privacy concerns around connected devices present reputational risks. The smart home market is expanding rapidly, and SmartHome Tech is well-positioned. Gross margins have improved as manufacturing scales up."
            },
            {
                "name": "BasicMaterials Corp",
                "ticker": "BMAT",
                "image": "https://via.placeholder.com/150?text=BMAT",
                "past_week_percent": -0.5,
                "short_description": "Mining and materials company producing industrial metals and minerals.",
                "detailed_description": "BasicMaterials Corp mines and processes copper, aluminum, and rare earth elements. The company's performance is closely tied to commodity prices and global economic conditions. Slight decline reflects concerns about manufacturing slowdown in key markets. However, long-term demand for materials needed in renewable energy and electric vehicles supports growth prospects. The company has low-cost mining operations and strong reserves. Environmental regulations pose compliance costs and operational challenges. Dividend yield is attractive compared to the broader market."
            }
        ]
    }
]

# Amount adjustments for each task (positive = gain, negative = loss)
AMOUNT_ADJUSTMENTS = {
    1: -50,   # Task 1: -50
    2: 75,    # Task 2: +75
    3: -120,  # Task 3: -120
    4: 200,   # Task 4: +200
    5: -80,   # Task 5: -80
    6: 150,   # Task 6: +150
    7: -100   # Task 7: -100
}
