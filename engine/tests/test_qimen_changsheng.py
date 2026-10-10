"""十二长生测试 — M3 批(师门第七章 + 补页;chang_sheng.py + wangshui-calc)。

书例锚定(补页第二节断局 + 附录A 宝典抽验):
- 己落巽四{辰巳}=衰+帝旺,年支戌(阳)→定性衰;流年:己 vs 辰=衰、vs 巳=帝旺;
- 乙落艮八{丑寅}=衰+帝旺(宝典抽验);乙 2018(戌)=墓、2019(亥)=死(补页例2);
- 癸落震三{卯}=长生(宝典抽验);癸落午=绝+壬落午=胎(补页例3 大运翻盘判);
- 中五宫不判(无本位地支,寄宫判法 gated 待师门)。
"""

from __future__ import annotations

import pytest
from qimen_engine.chang_sheng import (
    CHANG_SHENG_BIRTH,
    GONG_BRANCHES,
    TWELVE_STATES,
    branch_is_yang,
    chang_sheng_state,
    same_element_partner,
    zhang_sheng_primary,
    zhang_sheng_states,
)
from qimen_engine.data_tables import ZHI


class TestBirthTable:
    def test_full_table_per_book(self) -> None:
        """十干长生表全量(书行913-922):甲亥/丙戊寅/庚巳/壬申/乙午/丁己酉/辛子/癸卯。"""
        assert CHANG_SHENG_BIRTH == {
            "甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申",
            "乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯",
        }

    def test_twelve_states_order(self) -> None:
        assert TWELVE_STATES == (
            "长生", "沐浴", "冠带", "临官", "帝旺", "衰",
            "病", "死", "墓", "绝", "胎", "养",
        )

    def test_gong_branches_from_zhi2gong(self) -> None:
        """宫→本位地支(四正单支/四维双支/中五空)。"""
        assert GONG_BRANCHES == {
            1: ("子",), 8: ("丑", "寅"), 3: ("卯",), 4: ("辰", "巳"), 9: ("午",),
            2: ("未", "申"), 7: ("酉",), 6: ("戌", "亥"), 5: (),
        }
        for gong in (2, 4, 6, 8):  # 四维宫恒一阳一阴支(定性规则的前提)
            parities = {branch_is_yang(b) for b in GONG_BRANCHES[gong]}
            assert parities == {True, False}


class TestSequences:
    def test_jia_forward_sequence(self) -> None:
        """阳干顺排:甲自亥起长生,顺行十二支。"""
        branches = ("亥", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌")
        assert tuple(chang_sheng_state("甲", b) for b in branches) == TWELVE_STATES

    def test_yi_backward_sequence(self) -> None:
        """阴干逆排:乙自午起长生,逆行十二支。"""
        branches = ("午", "巳", "辰", "卯", "寅", "丑", "子", "亥", "戌", "酉", "申", "未")
        assert tuple(chang_sheng_state("乙", b) for b in branches) == TWELVE_STATES

    def test_bijection_all_stems(self) -> None:
        """每干十二支恰得十二态各一次(顺逆皆为置换)。"""
        for stem in CHANG_SHENG_BIRTH:
            states = {chang_sheng_state(stem, b) for b in ZHI}
            assert states == set(TWELVE_STATES), stem

    def test_birth_branch_is_chang_sheng(self) -> None:
        for stem, branch in CHANG_SHENG_BIRTH.items():
            assert chang_sheng_state(stem, branch) == "长生"


class TestBookAnchors:
    def test_ji_at_xun_gong_per_supplement(self) -> None:
        """补页例1:己落{辰巳}=衰+帝旺;年支戌(阳支)→取阳支辰,定性衰。"""
        assert zhang_sheng_states("己", 4) == [("辰", "衰"), ("巳", "帝旺")]
        assert zhang_sheng_primary("己", 4, "戌") == "衰"

    def test_ji_liu_nian_direct_lookup(self) -> None:
        """补页例1 流年:2024 甲辰→己落衰地;2025 乙巳→落帝旺。"""
        assert chang_sheng_state("己", "辰") == "衰"
        assert chang_sheng_state("己", "巳") == "帝旺"

    def test_yi_at_gen_gong_baodian(self) -> None:
        """宝典抽验:乙落艮{丑寅}=衰+帝旺。"""
        assert zhang_sheng_states("乙", 8) == [("丑", "衰"), ("寅", "帝旺")]

    def test_yi_2018_2019_per_supplement(self) -> None:
        """补页例2:乙 2018(戌)入墓、2019(亥)落死地。"""
        assert chang_sheng_state("乙", "戌") == "墓"
        assert chang_sheng_state("乙", "亥") == "死"

    def test_gui_at_zhen_gong_baodian(self) -> None:
        """宝典抽验:癸落震{卯}=长生。"""
        assert zhang_sheng_states("癸", 3) == [("卯", "长生")]

    def test_da_yun_flip_check_per_supplement(self) -> None:
        """补页例3:大运癸落绝地(午),看同五行壬——落胎地,亦不旺。"""
        assert chang_sheng_state("癸", "午") == "绝"
        assert same_element_partner("癸") == "壬"
        assert chang_sheng_state("壬", "午") == "胎"

    def test_same_element_partner_pairs(self) -> None:
        partners = [same_element_partner(s) for s in "甲乙丙丁戊己庚辛壬癸"]
        assert partners == list("乙甲丁丙己戊辛庚癸壬")


class TestPrimaryRules:
    def test_zhong_wu_returns_none(self) -> None:
        """中五宫不判:states 空 + primary None(寄宫判法 gated 待师门)。"""
        assert zhang_sheng_states("己", 5) == []
        assert zhang_sheng_primary("己", 5, "戌") is None

    def test_single_branch_palace_direct(self) -> None:
        """四正宫单支直返,年支阴阳不影响。"""
        assert zhang_sheng_primary("癸", 3, "戌") == "长生"
        assert zhang_sheng_primary("癸", 3, "亥") == "长生"

    def test_double_branch_parity_selection(self) -> None:
        """双支宫按年支阴阳取同阴阳之支:戌(阳)→辰=衰;亥(阴)→巳=帝旺。"""
        assert zhang_sheng_primary("己", 4, "戌") == "衰"
        assert zhang_sheng_primary("己", 4, "亥") == "帝旺"

    def test_validation_errors(self) -> None:
        with pytest.raises(ValueError):
            chang_sheng_state("禽", "子")
        with pytest.raises(ValueError):
            chang_sheng_state("甲", "禽")
        with pytest.raises(ValueError):
            zhang_sheng_states("甲", 0)
        with pytest.raises(ValueError):
            branch_is_yang("甲")
        with pytest.raises(ValueError):
            same_element_partner("子")
