import pandas as pd


def load_northwind(folder="data/northwind") -> dict:
    """Read every file as text so account numbers stay '6120', not 6120."""
    read = lambda name: pd.read_csv(f"{folder}/{name}.csv", dtype=str).fillna("")
    spend = read("ready_to_sync")
    spend["amount"] = spend["amount"].astype(float)
    return dict(spend=spend, entity_map=read("entity_map"), accounts=read("accounts"),
                vendors=read("vendors"), periods=read("periods"),
                mandatory=read("mandatory_fields"))


def _split(cell) -> set:
    return {s.strip() for s in str(cell).split(";") if s.strip()}


def preflight(spend, entity_map, accounts, vendors, periods, mandatory, catalog):
    ent = dict(zip(entity_map["ramp_entity"], entity_map["netsuite_subsidiary"]))
    acct = accounts.set_index("account")
    vend = vendors.set_index("vendor")
    open_periods = set(periods.loc[periods["status"] == "open", "period"])
    required = mandatory.groupby("object_type")["field"].apply(set).to_dict()

    issues = []

    def flag(rec, cid, **values):
        issues.append({**rec, "catalog_id": cid, "method": "preflight",
                       "confidence": 1.0, "note": "",
                       **{f"v_{k}": v for k, v in values.items()}})

    for rec in spend.to_dict("records"):
        sub = ent.get(rec["ramp_entity"], "")
        if not sub:
            flag(rec, "SUB-001")
            continue  # nothing else can be checked without a subsidiary

        a = rec["gl_account"]
        if a not in acct.index or acct.at[a, "active"].lower() != "yes":
            flag(rec, "GL-001", account=a)
        elif sub not in _split(acct.at[a, "subsidiaries"]):
            flag(rec, "GL-002", account=a)

        v = rec["vendor"]
        if v not in vend.index or vend.at[v, "active"].lower() != "yes":
            # NetSuite's VEN-001 error names the internal ID, not the vendor name.
            # Grouping by the same ID makes pre-flight and triage land in one group.
            vid = vend.at[v, "internal_id"] if v in vend.index else ""
            flag(rec, "VEN-001", internal_id=vid)
        elif sub not in _split(vend.at[v, "subsidiaries"]):
            flag(rec, "SUB-002", value=sub)

        if rec["date"][:7] not in open_periods:
            flag(rec, "PER-001")

        for f in required.get(rec["object_type"], set()):
            if not rec.get(f, "").strip():
                flag(rec, "REQ-001", field=f.title())

    result = pd.DataFrame(issues)
    if result.empty:
        return result
    details = catalog.drop(columns=["regex"])
    return result.merge(details, left_on="catalog_id", right_on="id", how="left")
