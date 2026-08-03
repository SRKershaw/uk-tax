from uk_tax.tax.tax_classes import tax_class_character


def test_gilts_and_qcbs_are_cgt_exempt():
    assert tax_class_character("gilt").gain_treatment == "exempt"
    assert tax_class_character("qcb").gain_treatment == "exempt"


def test_non_qcb_bond_is_chargeable_unlike_qcb():
    assert tax_class_character("non_qcb_bond").gain_treatment == "chargeable"


def test_offshore_non_reporting_gain_taxed_as_income():
    assert tax_class_character("offshore_non_reporting").gain_treatment == "taxed_as_income"


def test_commodity_has_no_income():
    assert tax_class_character("commodity").income_category is None


def test_equity_direct_is_dividend_income():
    assert tax_class_character("equity_direct").income_category == "dividends"


def test_cash_and_bonds_are_savings_income():
    assert tax_class_character("cash").income_category == "savings"
    assert tax_class_character("bond_fund_inc").income_category == "savings"
