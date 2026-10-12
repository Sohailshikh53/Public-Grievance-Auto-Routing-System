"""
Grievance Dataset Preparation and ML Model Training Pipeline
Public Grievance Auto-Routing System
"""

import json
import os
import random
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.pipeline import Pipeline
import joblib

from backend.config import CONFIDENCE_THRESHOLD

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(os.path.dirname(DATA_DIR), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

DEPARTMENTS = {
    "roads": "Roads & Footpaths",
    "water_supply": "Water Supply & Pipelines",
    "electricity": "Electricity & Streetlighting",
    "sanitation": "Solid Waste & Sanitation",
    "drainage": "Drainage & Sewerage",
    "public_health": "Public Health & Pest Control",
    "encroachment": "Encroachments & Town Planning"
}

BASE_DATA = [
    # Roads & Footpaths
    ("Deep pothole in the middle of main market road near clock tower causing vehicles to skid and accidents.", "roads", "HIGH"),
    ("Large crater on the road outside sector 4 gate, two wheeler fell yesterday evening.", "roads", "HIGH"),
    ("Road surface completely washed away after heavy rain near railway overbridge, only gravel left.", "roads", "MEDIUM"),
    ("Broken footpath tiles on MG Road creating severe walking hazard for elderly pedestrians.", "roads", "MEDIUM"),
    ("Divider stones smashed and lying on carriage way causing traffic blockage near bus stand.", "roads", "HIGH"),
    ("Asphalt peeled off on inner colony road number 5, metal gravel protruding everywhere.", "roads", "LOW"),
    ("Huge sinkhole opening up slowly near petrol pump intersection on station road.", "roads", "HIGH"),
    ("Footpath paver blocks completely removed by cable workers and left dug up for two weeks.", "roads", "MEDIUM"),
    ("Dangerous uneven road level after recent laying of telecom optical fiber trench.", "roads", "MEDIUM"),
    ("Speed breaker made without proper white marking or signboards causing sudden vehicle jumps.", "roads", "LOW"),
    ("Potholes filled with stagnant rainwater hiding their depth, multiple cyclists injured.", "roads", "HIGH"),
    ("Kerb stones broken along the arterial road leading to school, dangerous for children.", "roads", "MEDIUM"),
    ("Road dug up for pipeline work six months ago still not resurfaced, flying dust everywhere.", "roads", "MEDIUM"),
    ("Widened road corner has exposed sharp iron rods from concrete culvert.", "roads", "HIGH"),
    ("Damaged pedestrian walkway along highway flyover missing protective railings.", "roads", "HIGH"),
    ("Entire stretch of Shivaji Marg from circle to temple is full of deep ruts and cracks.", "roads", "MEDIUM"),
    ("Tar melted and deformed into dangerous ridges on highway bypass junction.", "roads", "LOW"),
    ("Open trench on roadside without barricade or safety warning ribbons.", "roads", "HIGH"),
    ("Pedestrian crossing stripes completely faded out near hospital zone.", "roads", "LOW"),
    ("Unpaved service road creating severe traffic bottlenecks and damage to vehicles.", "roads", "LOW"),

    # Water Supply & Pipelines
    ("No water supply in block C residential colony for the past three consecutive days.", "water_supply", "HIGH"),
    ("Water pressure is extremely low, not even filling ground floor storage tanks.", "water_supply", "MEDIUM"),
    ("Contaminated dirty brown water with strong foul chemical smell coming from kitchen taps.", "water_supply", "HIGH"),
    ("Major drinking water pipeline burst near municipal water tank, thousands of liters wasting onto street.", "water_supply", "HIGH"),
    ("Scheduled water tanker failed to arrive in slum rehabilitation colony, acute drinking water crisis.", "water_supply", "HIGH"),
    ("Muddy water with visible black sediment being supplied in ward 12 since morning.", "water_supply", "HIGH"),
    ("Water supply timing changed without prior notification, arriving at 2 AM for only 15 minutes.", "water_supply", "MEDIUM"),
    ("Underground main pipeline leaking continuously, seepage entering basement of building.", "water_supply", "HIGH"),
    ("Air lock in society municipal water connection preventing flow to upper floors.", "water_supply", "LOW"),
    ("Worm like larvae found in overhead supply water in shastri nagar sector 2.", "water_supply", "HIGH"),
    ("Defective water meter installed by department recording excessive billing despite zero supply.", "water_supply", "LOW"),
    ("Municipal water valve near community hall damaged and jammed in shut position.", "water_supply", "MEDIUM"),
    ("Sewage water mixing into drinking water pipeline, residents falling sick with vomiting.", "water_supply", "HIGH"),
    ("Severe scarcity of potable water in ward 8, requested emergency tanker not dispatched.", "water_supply", "HIGH"),
    ("Water supply stopped abruptly during morning hours without any scheduled maintenance alert.", "water_supply", "MEDIUM"),
    ("Corroded galvanized iron pipeline connection broken at consumer junction box.", "water_supply", "LOW"),
    ("Turbid and yellowish water supplied during morning cycle, unfit for cooking and consumption.", "water_supply", "HIGH"),
    ("Illegal motor pump suction installed by neighbor dropping pressure for entire street.", "water_supply", "MEDIUM"),
    ("Water pipeline leakage causing dampness and structural risk to boundary wall.", "water_supply", "MEDIUM"),
    ("Drinking water smells strongly of bleaching powder and industrial waste.", "water_supply", "HIGH"),

    # Electricity & Streetlighting
    ("Streetlight pole number 24 on main avenue is not working for past one week, pitch dark road.", "electricity", "MEDIUM"),
    ("Live electrical wire snapped and dangling loose near primary school gate, life hazard.", "electricity", "HIGH"),
    ("Frequent power tripping and low voltage damaging home appliances in pocket B.", "electricity", "MEDIUM"),
    ("Distribution transformer sparking violently with loud explosive noise near market complex.", "electricity", "HIGH"),
    ("Streetlights remain switched on during bright daylight for last 10 days wasting public electricity.", "electricity", "LOW"),
    ("Rusted electric pole leaning dangerously over footpath, likely to collapse in strong wind.", "electricity", "HIGH"),
    ("Underground power cable burnt out, entire residential street in complete darkness since night.", "electricity", "HIGH"),
    ("Electric feeder pillar box left open with exposed live busbars accessible to children.", "electricity", "HIGH"),
    ("Streetlights flickering continuously creating severe visibility issues for nighttime motorists.", "electricity", "LOW"),
    ("Phase failure on phase 3 causing half the houses in lane 6 to lose power.", "electricity", "MEDIUM"),
    ("Overhead high tension wire sagging below minimum clearance height above road.", "electricity", "HIGH"),
    ("Sodium vapor streetlamp fixture hanging by a single loose wire ready to fall on pedestrians.", "electricity", "HIGH"),
    ("Dark spot on university road due to three consecutive broken streetlights, unsafe for women.", "electricity", "HIGH"),
    ("Electric meter box sparking on utility pole after light drizzle this afternoon.", "electricity", "HIGH"),
    ("Automatic timer for streetlights broken, lights do not turn on even after 8 PM.", "electricity", "MEDIUM"),
    ("Short circuit in municipal street feeder board emitting burning plastic odor.", "electricity", "HIGH"),
    ("Replacement bulb requested for pole number 18 not installed despite multiple reminders.", "electricity", "LOW"),
    ("Uninsulated junction box on roadside pole sparking when touched by rain.", "electricity", "HIGH"),
    ("Complete blackout on ring road sector due to sub-station line trip.", "electricity", "HIGH"),
    ("Streetlight cover glass broken, bulb exposed to rain and blowing fuses repeatedly.", "electricity", "LOW"),

    # Solid Waste & Sanitation
    ("Huge garbage dump accumulated near community dustbin not cleared for five days, foul smell.", "sanitation", "HIGH"),
    ("Door to door municipal waste collection vehicle has not visited our street since Monday.", "sanitation", "MEDIUM"),
    ("Dead dog carcass lying on the corner of 4th cross road, flies and terrible stench.", "sanitation", "HIGH"),
    ("Garbage bin overturned by stray cattle, rotten food waste strewn across entire street.", "sanitation", "MEDIUM"),
    ("Sanitation sweepers not sweeping colony roads, dry leaves and plastic wrappers piling up.", "sanitation", "LOW"),
    ("Illegal commercial dumping of poultry waste and rotting meat behind vegetable market.", "sanitation", "HIGH"),
    ("Waste collection vehicle workers refusing to collect segregated dry waste from households.", "sanitation", "LOW"),
    ("Open garbage vat overflowing into neighboring residential compounds.", "sanitation", "HIGH"),
    ("Litter bins installed near bus stand damaged and overflowing with empty plastic bottles.", "sanitation", "LOW"),
    ("Construction rubble and broken glass bottles dumped overnight on public garden perimeter.", "sanitation", "MEDIUM"),
    ("Sanitation staff burning collected dry plastic waste on roadside causing suffocating smoke.", "sanitation", "HIGH"),
    ("Decomposed animal remains near open ground attracting vultures and wild animals.", "sanitation", "HIGH"),
    ("Commercial restaurant dumping greasy food waste into municipal open drum directly.", "sanitation", "MEDIUM"),
    ("No public dustbin provided along busy market stretch, forcing people to throw trash on street.", "sanitation", "LOW"),
    ("Overflowing community dumper bin blocking pedestrian movement near dispensary.", "sanitation", "MEDIUM"),
    ("Solid waste collection truck leaking foul black leachate liquid all over the road during transit.", "sanitation", "HIGH"),
    ("Colony park filled with uncollected plastic garbage and food packaging after weekend event.", "sanitation", "MEDIUM"),
    ("Sanitation worker demanding illicit money to collect household organic waste.", "sanitation", "MEDIUM"),
    ("Fish market waste dumped openly on road edge creating extreme nuisance and pest issues.", "sanitation", "HIGH"),
    ("Garbage compactor breakdown led to piles of garbage rotting in sun for 72 hours.", "sanitation", "HIGH"),

    # Drainage & Sewerage
    ("Underground sewer line blocked and overflowing dirty sewage onto residential road.", "drainage", "HIGH"),
    ("Manhole cover broken and missing on busy lane, open death trap for vehicles and children.", "drainage", "HIGH"),
    ("Stormwater drain completely choked with silt and plastic debris causing waterlogging after rain.", "drainage", "HIGH"),
    ("Sewage water backflowing into ground floor bathrooms and toilets of apartment block.", "drainage", "HIGH"),
    ("Open roadside gutter overflowing with black foul sludge and spreading onto walking track.", "drainage", "HIGH"),
    ("Broken concrete slab over stormwater drain causing vehicles to fall in during turns.", "drainage", "MEDIUM"),
    ("Severe stench of rotten sewer gas emanating from blocked municipal drain junction.", "drainage", "MEDIUM"),
    ("Drainage pipe connection damaged during road excavation, wastewater flooding cellars.", "drainage", "HIGH"),
    ("Storm water canal blocked by fallen branches and mud preventing rainwater runoff.", "drainage", "MEDIUM"),
    ("Uncovered sewer inspection chamber on school route emitting foul gases without lid.", "drainage", "HIGH"),
    ("Heavy sewage overflow near local temple causing devotees to walk through contaminated water.", "drainage", "HIGH"),
    ("Drainage desilting work left halfway, excavated wet silt left on road washing back into drain.", "drainage", "MEDIUM"),
    ("Main underground sewer line collapsed creating sudden crater and sewage lake in sector 9.", "drainage", "HIGH"),
    ("Gutter wall collapsed causing wastewater to seep into foundations of adjacent houses.", "drainage", "HIGH"),
    ("Clogged street drain causing ankle deep filthy water accumulation after slight rain.", "drainage", "MEDIUM"),
    ("Manhole chamber sinking below road level creating deep hazard for two wheelers.", "drainage", "MEDIUM"),
    ("Sanitary sewer chamber overflowing with toilet paper and untreated human waste onto street.", "drainage", "HIGH"),
    ("Pre monsoon cleaning of major nullah not carried out, risk of flood in low lying areas.", "drainage", "HIGH"),
    ("Kitchen wastewater from commercial hotels being discharged directly into open stormwater channel.", "drainage", "MEDIUM"),
    ("Rainwater catchment drain grating stolen by scrap collectors, leaving dangerous gap.", "drainage", "HIGH"),

    # Public Health & Pest Control
    ("Severe mosquito menace in ward 7 due to stagnant water pool, urgent fogging required.", "public_health", "HIGH"),
    ("Multiple cases of dengue and chikungunya reported in our lane, please arrange insecticide spray.", "public_health", "HIGH"),
    ("Pack of aggressive stray dogs chasing two wheeler riders and biting children near playground.", "public_health", "HIGH"),
    ("Unhygienic roadside meat stall operating without municipal health license in open dust.", "public_health", "MEDIUM"),
    ("Stagnant green pool of water in abandoned municipal plot acting as massive mosquito nursery.", "public_health", "HIGH"),
    ("Request for anti-larval chemical treatment and malathion thermal fogging in entire sector.", "public_health", "MEDIUM"),
    ("Stray dog menace outside district hospital, patients and relatives unable to enter safely.", "public_health", "HIGH"),
    ("Food poisoning outbreak reported from uninspected street food vendor near college gate.", "public_health", "HIGH"),
    ("Huge rat and rodent infestation near grain warehouse causing public health hazard.", "public_health", "MEDIUM"),
    ("Mosquito larvae floating in accumulated water near municipal garden fountain.", "public_health", "MEDIUM"),
    ("Rabid stray dog suspected in locality, bit two pedestrians this morning, catch immediately.", "public_health", "HIGH"),
    ("Foul smell and fly breeding from illegal dairy farm functioning in dense residential colony.", "public_health", "MEDIUM"),
    ("Health department has not conducted seasonal anti-dengue door to door larvae inspection.", "public_health", "LOW"),
    ("Stray cattle and dog fighting near vegetable market creating panic and injuries.", "public_health", "MEDIUM"),
    ("Need fogging vehicle to visit lane 4 and 5 due to surge in viral fever cases among children.", "public_health", "HIGH"),
    ("Open sale of rotten cut fruits and adulterated ice cubes outside school premises.", "public_health", "MEDIUM"),
    ("Stagnant water in open cooling towers causing heavy mosquito breeding and foul odor.", "public_health", "MEDIUM"),
    ("Pest control spraying overdue for government dispensary building and surroundings.", "public_health", "LOW"),
    ("Aggressive stray monkey troupe attacking residents on terrace and snatching food.", "public_health", "MEDIUM"),
    ("No health inspector visited unhygienic slaughterhouse dumping blood in residential gutter.", "public_health", "HIGH"),

    # Encroachments & Town Planning
    ("Illegal tea stall and vendor carts permanently occupying pedestrian footpath on station road.", "encroachment", "MEDIUM"),
    ("Unauthorized commercial concrete extension built beyond legal boundary onto public street.", "encroachment", "HIGH"),
    ("Shopkeeper erected permanent iron shed and ramp over municipal sidewalk blocking pedestrians.", "encroachment", "MEDIUM"),
    ("Construction company dumped steel rods and gravel mounds on road lane blocking traffic.", "encroachment", "HIGH"),
    ("Illegal billboard and advertising hoarding erected on road intersection without permit.", "encroachment", "MEDIUM"),
    ("Street hawkers encroached both sides of vegetable market road leaving zero space for ambulances.", "encroachment", "HIGH"),
    ("Unauthorized vehicle repair shop using entire public pavement as their private workshop.", "encroachment", "MEDIUM"),
    ("Illegal gate installed by private society on public road restricting common public access.", "encroachment", "HIGH"),
    ("Footpath encroached by permanent stone stairs constructed by commercial showroom.", "encroachment", "MEDIUM"),
    ("Unauthorized temporary tents and shanties erected on municipal playground land.", "encroachment", "HIGH"),
    ("Scrap merchant operating illegally on vacant municipal land with heavy trucks blocking lane.", "encroachment", "MEDIUM"),
    ("Commercial parking mafia encroached public lane and charging illegal parking fees.", "encroachment", "HIGH"),
    ("Temporary fruit vendor wooden shacks occupying half the carriage width on flyover descent.", "encroachment", "HIGH"),
    ("Building owner undertaking unauthorized construction of 4th floor violating sanctioned building plan.", "encroachment", "HIGH"),
    ("Illegal generator set placed permanently on public walking pavement by banquet hall.", "encroachment", "MEDIUM"),
    ("Unauthorized cow shelter built on public road corner obstructing vision of drivers.", "encroachment", "MEDIUM"),
    ("Encroachment of public green belt and park boundary by adjoining residential plot owners.", "encroachment", "MEDIUM"),
    ("Pavement completely blocked by parked unregistered commercial vehicles and junk cabs.", "encroachment", "MEDIUM"),
    ("Illegal tin shed erected on government land near bus terminal housing unauthorized store.", "encroachment", "HIGH"),
    ("Hawkers setting up open stalls right in front of emergency fire exit of shopping arcade.", "encroachment", "HIGH"),

    # AMBIGUOUS / BORDERLINE CASES (Designed to trigger confidence fallback to Manual Review!)
    ("There is a terrible problem near my house since three days, please send an officer to inspect.", "roads", "MEDIUM"),
    ("Dirty water coming onto the street near the big pothole, causing huge trouble.", "drainage", "HIGH"),
    ("Electricity wire touching the iron sign of the illegal fruit stall on the corner.", "electricity", "HIGH"),
    ("Water is leaking from pipe and mixing with garbage on the road outside temple.", "water_supply", "HIGH"),
    ("Please check ward 5 immediately, people are facing a lot of civic issues every day.", "sanitation", "LOW"),
    ("Unbearable foul smell near the junction, unable to breathe properly while passing.", "sanitation", "MEDIUM"),
    ("Municipal worker did not show up today and area is in very bad condition.", "sanitation", "LOW"),
    ("Construction work happening near the open gutter and causing problems to traffic.", "encroachment", "MEDIUM"),
    ("Very bad situation outside our colony gate, kindly take prompt action.", "roads", "LOW"),
    ("Water logging near electric pole, fear of electrocution during night time.", "electricity", "HIGH"),
    ("Broken slab with water leaking and bad smell, please look into this urgency.", "drainage", "HIGH"),
    ("Can someone inspect the corner of 2nd cross road, it is completely neglected.", "sanitation", "LOW"),
]

# Variations and data augmentation to build realistic dataset of 600+ complaints
LOCATIONS = [
    "near Railway Station", "outside Civil Hospital", "at Shivaji Chowk", "in Sector 14",
    "on MG Road", "near Bus Stand", "in Ward 4", "behind Market Yard", "near Gandhi Putla",
    "at Azad Maidan", "in Shastri Nagar", "on Ring Road", "near Subhash Garden",
    "outside Government School", "in Model Colony", "near Petrol Pump", "at Clock Tower"
]

PREFIXES = [
    "Kindly look into this issue: ",
    "Urgent grievance regarding: ",
    "Sir, we are facing serious trouble: ",
    "Complaint for immediate redressal: ",
    "Dear Municipal Officer, ",
    "Attention grievance cell: ",
    "Repeated issue reported: ",
    ""
]

SUFFIXES = [
    " Please take immediate action.",
    " We have complained before but no response.",
    " It has been causing hardship to residents for days.",
    " Kindly dispatch departmental team at earliest.",
    " Hope this gets resolved without delay.",
    " Action requested before situation worsens.",
    ""
]

def generate_full_dataset(target_size=700):
    random.seed(42)
    records = []
    
    # Add all base data
    for base_id, (text, dept, urg) in enumerate(BASE_DATA):
        records.append({
            "complaint_text": text,
            "department": dept,
            "urgency": urg,
            "ward_number": f"Ward {random.randint(1, 15)}",
            "is_ambiguous": "ambiguous" in text.lower() or len(text.split()) < 10,
            "base_group": base_id,
        })
        
    # Generate variations with locations and realistic phrasing
    while len(records) < target_size:
        base_id = random.randrange(len(BASE_DATA))
        base_item = BASE_DATA[base_id]
        text, dept, urg = base_item
        
        prefix = random.choice(PREFIXES)
        suffix = random.choice(SUFFIXES)
        loc = random.choice(LOCATIONS)
        
        # Modify text naturally
        var_text = f"{prefix}{text} Located {loc}.{suffix}".strip()
        ward = f"Ward {random.randint(1, 15)}"
        
        records.append({
            "complaint_text": var_text,
            "department": dept,
            "urgency": urg,
            "ward_number": ward,
            "is_ambiguous": False,
            "base_group": base_id,
        })
        
    df = pd.DataFrame(records)
    return df

def train_and_evaluate(df):
    X = df["complaint_text"]
    y = df["department"]
    
    # Keep every paraphrase of a base complaint in the same split. This prevents
    # near-duplicate template leakage and produces a more honest evaluation.
    split_rng = random.Random(42)
    held_out_groups = set()
    for department in sorted(df["department"].unique()):
        groups = sorted(df.loc[df["department"] == department, "base_group"].unique())
        held_out_groups.update(split_rng.sample(groups, max(1, round(len(groups) * 0.20))))
    test_mask = df["base_group"].isin(held_out_groups).to_numpy()
    test_idx = np.flatnonzero(test_mask)
    train_idx = np.flatnonzero(~test_mask)
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    
    pipeline = Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(
                ngram_range=(1, 2), max_features=5000,
                sublinear_tf=True, stop_words="english"
            )),
            ("character", TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5), max_features=7000,
                sublinear_tf=True
            )),
        ])),
        ("classifier", LogisticRegression(
            C=8.0,
            max_iter=1000,
            solver="lbfgs"
        ))
    ])
    
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)
    classes = list(pipeline.classes_)
    
    acc = float(accuracy_score(y_test, y_pred))
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred, labels=classes).tolist()
    
    # Confidence distribution
    max_probas = [float(np.max(p)) for p in y_proba]
    conf_below_threshold = [p for p in max_probas if p < CONFIDENCE_THRESHOLD]
    fallback_rate = len(conf_below_threshold) / len(max_probas)
    
    # Save model pipeline
    model_path = os.path.join(MODELS_DIR, "grievance_classifier.joblib")
    joblib.dump(pipeline, model_path)
    
    # Save metadata & evaluation results
    eval_results = {
        "model_type": "Word + character TF-IDF ensemble with multiclass logistic regression",
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "overall_accuracy": round(acc, 4),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "test_fallback_rate": round(fallback_rate, 4),
        "evaluation_protocol": "Group-held-out split by source complaint template to prevent paraphrase leakage",
        "classes": classes,
        "class_labels": [DEPARTMENTS.get(c, c) for c in classes],
        "confusion_matrix": cm,
        "classification_report": {
            k: {
                "precision": round(v["precision"], 4),
                "recall": round(v["recall"], 4),
                "f1_score": round(v["f1-score"], 4),
                "support": v["support"]
            }
            for k, v in report.items() if isinstance(v, dict)
        }
    }
    
    eval_path = os.path.join(MODELS_DIR, "model_evaluation.json")
    with open(eval_path, "w") as f:
        json.dump(eval_results, f, indent=2)
        
    print(f"Model successfully trained and saved to: {model_path}")
    print(f"Model evaluation saved to: {eval_path}")
    print(f"Accuracy: {acc * 100:.2f}%")
    print(f"Test samples: {len(X_test)}, Training samples: {len(X_train)}")
    print(f"Confidence fallback rate on test set (below {CONFIDENCE_THRESHOLD}): {fallback_rate * 100:.2f}%")
    
    return pipeline, eval_results

if __name__ == "__main__":
    df = generate_full_dataset(target_size=750)
    dataset_path = os.path.join(DATA_DIR, "grievance_dataset.csv")
    df.to_csv(dataset_path, index=False)
    print(f"Saved dataset with {len(df)} records to {dataset_path}")
    
    pipeline, eval_results = train_and_evaluate(df)
