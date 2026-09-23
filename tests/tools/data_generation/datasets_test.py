import json

from src.tools.data_generation.affixes import generate_affixes
from src.tools.data_generation.datasets import (
    generate_aspects,
    generate_set_aliases,
    generate_sets,
    generate_sigils,
    generate_uniques,
    main,
    string_list_value,
)


def test_get_string_list_name_returns_a_stable_name() -> None:
    assert string_list_value({"arStrings": [{"szLabel": "name", "szText": "Example"}]}, "name") == "Example"


def test_main_reports_stage_start_finish_counts_and_elapsed_time(tmp_path, monkeypatch, capsys) -> None:
    string_list_dir = tmp_path / "d4data/json/enUS_Text/meta/StringList"
    string_list_dir.mkdir(parents=True)
    (string_list_dir / "UIToolTips.stl.json").write_text('{"arStrings": []}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)
    for stage in ("aspects", "uniques", "sets", "sigils", "affixes"):
        monkeypatch.setattr(f"src.tools.data_generation.datasets.generate_{stage}", lambda *_args, **_kwargs: 7)

    main(tmp_path / "d4data")

    output = capsys.readouterr().out
    assert "START aspects" in output
    assert "SKIP koKR:" in output
    assert "FINISH aspects: 7 files, elapsed=" in output
    assert "FINISH tributes:" in output
    assert "FINISH item_types:" in output
    assert "FINISH tooltips:" in output
    assert "FINISH affixes: 7 files, elapsed=" in output


def test_main_preserves_generic_axe_and_sword_item_type_labels(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    string_list_dir = d4data / "json/enUS_Text/meta/StringList"
    string_list_dir.mkdir(parents=True)
    (string_list_dir / "UIToolTips.stl.json").write_text('{"arStrings": []}', encoding="utf-8")
    for item_type, name in (
        ("Axe", "axe"),
        ("Axe_Berserker_Axe", "berserker axe"),
        ("Sword", "sword"),
        ("Sword_Phase_Blade", "phase blade"),
    ):
        (string_list_dir / f"ItemType_{item_type}.stl.json").write_text(
            json.dumps({"arStrings": [{"szLabel": "Name", "szText": name}]}), encoding="utf-8"
        )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)
    for stage in ("aspects", "uniques", "sets", "sigils", "affixes"):
        monkeypatch.setattr(f"src.tools.data_generation.datasets.generate_{stage}", lambda *_args, **_kwargs: 0)

    main(d4data)

    output = json.loads((tmp_path / "assets/lang/enUS/item_types.json").read_text(encoding="utf-8"))
    assert output["Axe"] == "axe"
    assert output["Sword"] == "sword"


def test_affix_generation_uses_core_toc_power_index_without_parsing_power_files(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    string_dir = d4data / "json/enUS_Text/meta/StringList"
    (d4data / "json/base/meta/Affix").mkdir(parents=True)
    (d4data / "json/base/meta/Power").mkdir(parents=True)
    string_dir.mkdir(parents=True)
    empty_strings = '{"arStrings": []}'
    for name in ("AttributeDescriptions", "ItemRequirements", "NecromancerArmy", "SkillTags", "UIToolTips"):
        (string_dir / f"{name}.stl.json").write_text(empty_strings, encoding="utf-8")
    (d4data / "json/base/CoreTOC.dat.json").write_text('{"29": {"42": "Power_example"}}', encoding="utf-8")
    (d4data / "json/GBID.json").write_text("{}", encoding="utf-8")
    (d4data / "json/base/meta/Power/invalid.json").write_text("not json", encoding="utf-8")
    for index in range(3):
        (d4data / f"json/base/meta/Affix/Affix_{index}.json").write_text(
            json.dumps({
                "__fileName__": f"Affix_{index}.json",
                "eMagicType": 0,
                "ptItemAffixAttributes": [{"tAttribute": {"__eAttribute_name__": "Missing"}}],
            }),
            encoding="utf-8",
        )
    output_dir = tmp_path / "assets/lang/enUS"
    output_dir.mkdir(parents=True)
    monkeypatch.setattr("src.tools.data_generation.affixes.D4LF_BASE_DIR", tmp_path)

    sequential = tmp_path / "sequential.json"
    generate_affixes(d4data, "enUS", sequential)

    assert sequential.exists()


def test_generate_uniques_skips_placeholder_before_reading_incomplete_inherent_affix(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    unique_dir = d4data / "json/base/meta/Item"
    string_dir = d4data / "json/enUS_Text/meta/StringList"
    unique_dir.mkdir(parents=True)
    string_dir.mkdir(parents=True)
    (unique_dir / "Placeholder_Unique.itm.json").write_text(
        json.dumps({
            "snoItemType": {"name": "Sword"},
            "arForcedAffixes": [{"name": "forced_affix"}],
            "arInherentAffixes": [{}],
        }),
        encoding="utf-8",
    )
    (string_dir / "Item_Placeholder_Unique.stl.json").write_text(
        json.dumps({"arStrings": [{"szLabel": "Name", "szText": "[PH] Placeholder Unique"}]}), encoding="utf-8"
    )
    output_dir = tmp_path / "assets/lang/enUS"
    output_dir.mkdir(parents=True)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)

    assert generate_uniques(d4data, "enUS") == 1

    output = json.loads((output_dir / "uniques.json").read_text(encoding="utf-8"))
    assert "[ph]_placeholder_unique" not in output
    assert output == {}


def test_korean_unique_generation_keeps_english_key_and_stores_localized_alias(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    unique_dir = d4data / "json/base/meta/Item"
    unique_dir.mkdir(parents=True)
    for language, text in (("enUS", "Godslayer Crown"), ("koKR", "신 살해자 왕관")):
        string_dir = d4data / f"json/{language}_Text/meta/StringList"
        string_dir.mkdir(parents=True)
        (string_dir / "Item_Unique_Godslayer_Crown.stl.json").write_text(
            json.dumps({"arStrings": [{"szLabel": "Name", "szText": text}]}), encoding="utf-8"
        )
    (unique_dir / "Unique_Godslayer_Crown.itm.json").write_text(
        json.dumps({
            "snoItemType": {"name": "Helm"},
            "arForcedAffixes": [{"name": "forced_affix"}],
            "arInherentAffixes": [],
        }),
        encoding="utf-8",
    )
    output_dir = tmp_path / "assets/lang/koKR"
    output_dir.mkdir(parents=True)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)

    generate_uniques(d4data, "koKR")

    output = json.loads((output_dir / "uniques.json").read_text(encoding="utf-8"))
    assert output == {"godslayer_crown": {"localized_name": "신_살해자_왕관", "num_inherents": 0}}


def test_korean_sigil_generation_keeps_english_keys_and_stores_aliases(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    world_dir = d4data / "json/base/meta/World"
    affix_dir = d4data / "json/base/meta/DungeonAffix"
    world_dir.mkdir(parents=True)
    affix_dir.mkdir(parents=True)
    (world_dir / "DGN_Test.wrl.json").write_text("{}", encoding="utf-8")
    (affix_dir / "Minor_Test.dax.json").write_text("{}", encoding="utf-8")
    for language, dungeon, affix, desc in (
        ("enUS", "Beast Graveyard", "Hellbound Elites", "Elite monsters are stronger."),
        ("koKR", "야수 무덤", "지옥결속 정예", "정예 괴물이 더 강해집니다."),
    ):
        string_dir = d4data / f"json/{language}_Text/meta/StringList"
        string_dir.mkdir(parents=True)
        (string_dir / "World_DGN_Test.stl.json").write_text(
            json.dumps({"arStrings": [{"szLabel": "Name", "szText": dungeon}]}), encoding="utf-8"
        )
        (string_dir / "DungeonAffix_Minor_Test.stl.json").write_text(
            json.dumps({
                "arStrings": [
                    {"szLabel": "AffixName", "szText": affix},
                    {"szLabel": "AffixDesc", "szText": desc},
                ]
            }),
            encoding="utf-8",
        )
    output_dir = tmp_path / "assets/lang/koKR"
    output_dir.mkdir(parents=True)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)

    generate_sigils(d4data, "koKR")

    output = json.loads((output_dir / "sigils.json").read_text(encoding="utf-8"))
    assert output["dungeons"] == {"beast_graveyard": "야수 무덤"}
    assert output["minor"] == {"hellbound_elites": "지옥결속 정예 정예 괴물이 더 강해집니다."}
    assert output["aliases"] == {"야수_무덤": "beast_graveyard", "지옥결속_정예": "hellbound_elites"}


def test_korean_aspect_generation_keeps_english_names(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    aspect_dir = d4data / "json/base/meta/Aspect"
    aspect_dir.mkdir(parents=True)
    (aspect_dir / "Aspect_Test.asp.json").write_text(
        json.dumps({"snoAffix": {"name": "Test_Aspect"}}), encoding="utf-8"
    )
    for language, text in (("enUS", "Aspect of Testing"), ("koKR", "시험의 위상")):
        string_dir = d4data / f"json/{language}_Text/meta/StringList"
        string_dir.mkdir(parents=True)
        (string_dir / "Affix_Test_Aspect.stl.json").write_text(
            json.dumps({"arStrings": [{"szLabel": "Name", "szText": text}]}), encoding="utf-8"
        )
    output_dir = tmp_path / "assets/lang/koKR"
    output_dir.mkdir(parents=True)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)

    generate_aspects(d4data, "koKR")

    output = json.loads((output_dir / "aspects.json").read_text(encoding="utf-8"))
    assert output == ["aspect_of_testing"]


def test_korean_set_generation_keeps_english_names_and_aliases_can_be_generated(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    charm_dir = d4data / "json/base/meta/Item"
    charm_dir.mkdir(parents=True)
    (charm_dir / "Talisman_Charm_Test.itm.json").write_text(
        json.dumps({"snoItemType": {"name": "Charm"}, "snoSetItemBonus": {"name": "Test_Set"}}),
        encoding="utf-8",
    )
    for language, text in (("enUS", "Arms of Testing"), ("koKR", "시험의 무장")):
        string_dir = d4data / f"json/{language}_Text/meta/StringList"
        string_dir.mkdir(parents=True)
        (string_dir / "SetItemBonus_Test_Set.stl.json").write_text(
            json.dumps({"arStrings": [{"szLabel": "Name", "szText": text}]}), encoding="utf-8"
        )
    output_dir = tmp_path / "assets/lang/koKR"
    output_dir.mkdir(parents=True)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)

    generate_sets(d4data, "koKR")

    output = json.loads((output_dir / "sets.json").read_text(encoding="utf-8"))
    assert output == ["arms_of_testing"]
    assert generate_set_aliases(d4data, "koKR") == {"시험의_무장": "arms_of_testing"}


def test_main_copies_shared_corrections_for_korean_generation(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    for language in ("enUS", "koKR"):
        string_dir = d4data / f"json/{language}_Text/meta/StringList"
        string_dir.mkdir(parents=True)
        (string_dir / "UIToolTips.stl.json").write_text('{"arStrings": []}', encoding="utf-8")
    corrections_dir = tmp_path / "assets/lang/enUS"
    corrections_dir.mkdir(parents=True)
    (corrections_dir / "corrections.json").write_text('{"filter_after_keyword": [], "filter_words": [], "bad_tts_uniques": {}}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)
    for stage in ("aspects", "uniques", "sets", "sigils", "affixes"):
        monkeypatch.setattr(f"src.tools.data_generation.datasets.generate_{stage}", lambda *_args, **_kwargs: 0)

    main(d4data)

    assert (tmp_path / "assets/lang/koKR/corrections.json").read_text(encoding="utf-8") == (
        '{"filter_after_keyword": [], "filter_words": [], "bad_tts_uniques": {}}'
    )
