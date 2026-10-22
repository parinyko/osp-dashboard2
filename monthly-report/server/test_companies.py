from server.companies import OTHER_ZONE, EXPRESS_RESERVE, classify, company_of, mnm_area, zone_order


def zt(company, assign, zid=None):
    c = classify(company, assign, zid)
    return c["slug"], c["zone"], c["team"]


def test_company_slugs():
    assert company_of("DMP Advance Solution Network")[0] == "dmp"
    assert company_of("Origin Fiber")[0] == "origin"
    assert company_of("Ex-Press Data Network")[0] == "express"
    assert company_of("Express Data Network")[0] == "express"
    assert company_of("3BB")[0] == "3bb"
    assert company_of("NY CABLE")[0] == "nycable"
    assert company_of("Brand New Co., Ltd.")[0] == "brand-new-co-ltd"
    assert company_of(None)[0] == "unknown"


def test_dmp_matches_original_report():
    assert zt("DMP Advance Solution Network", "Dmplocallatkrabang A") == ("dmp", "Latkrabang", "Dmplocallatkrabang A")
    assert zt("DMP Advance Solution Network", "dmplocalPathumthani c") == ("dmp", "Pathumthani", "Dmplocalpathumthani C")
    assert zt("DMP Advance Solution Network", "Apmdmp A")[1] == OTHER_ZONE


def test_origin():
    assert zt("Origin Fiber", "Originlocalthungkhru B") == ("origin", "Thungkhru", "Originlocalthungkhru B")
    assert zt("Origin Fiber", "Originlocalnonthaburi A")[1] == "Nonthaburi"
    assert zt("Origin Fiber", "Originlocal Center") == ("origin", "Center", "Originlocal Center")


def test_express_accounts_and_tiers():
    ex = "Ex-Press Data Network"
    assert zt(ex, "Exbpl A") == ("express", "BPL", "Exbpl A")
    assert zt(ex, "Extrcwt H") == ("express", "CWT", "Extrcwt H")
    assert zt(ex, "Expressminibpl Phongdanai") == ("express", "BPL", "BPL Mini")
    assert zt(ex, "Expressmacrotlc Boonchuay") == ("express", "TLC", "TLC Macro")
    assert zt(ex, "Expressmarcocwt Somchai") == ("express", "CWT", "CWT Macro")  # typo in source data
    assert zt(ex, "Expressmacroibpl Adee") == ("express", "BPL", "BPL Macro")    # typo in source data
    assert zt(ex, "Expresseds Suksan") == ("express", "EDS", "EDS Express")
    assert zt(ex, "Poonpoob Kitisriworaphan") == ("express", EXPRESS_RESERVE, "Poonpoob Kitisriworaphan")
    assert zt(ex, "Expresshighloss A")[1] == EXPRESS_RESERVE
    assert zt(ex, "Exspare A")[1] == EXPRESS_RESERVE


def test_express_team_order_accounts_then_tiers():
    ex = "Ex-Press Data Network"
    names = ["BPL Macro", "Exbpl B", "BPL Mini", "Extrbpl F", "Exbpl A"]
    keys = {}
    for n, a in zip(names, ["Expressmacrobpl X", "Exbpl B", "Expressminibpl Y", "Extrbpl F", "Exbpl A"]):
        keys[classify(ex, a, None)["team"]] = classify(ex, a, None)["sort"]
    ordered = [t for t, _ in sorted(keys.items(), key=lambda kv: (kv[1], kv[0]))]
    assert ordered == ["Exbpl A", "Exbpl B", "Extrbpl F", "BPL Mini", "BPL Macro"]


def test_mnm_companies():
    assert mnm_area("MNM-AREA2 (Bangkok-ONT)") == (2, "ONT")
    assert mnm_area("MC4_LPG (North)") is None
    assert zt("3BB", "Preecha Ruamsungneon", "MNM-AREA3 (Bangkok-TLC)") == ("3bb", "TLC", "Preecha Ruamsungneon")
    assert zt("NY CABLE", "Nyc Nana", None)[1] == OTHER_ZONE


def test_zone_order():
    assert zone_order("express", "express", {"TLC": None, "SCT": None, EXPRESS_RESERVE: None}) == ["SCT", "TLC", EXPRESS_RESERVE]
    assert zone_order("3bb", "mnm", {"CWT": 4, "ST2": 1, OTHER_ZONE: None, "ONT": 2}) == ["ST2", "ONT", "CWT"]
