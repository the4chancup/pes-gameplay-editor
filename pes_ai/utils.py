from io import BytesIO
from struct import pack, unpack

bools = [
    ## match
    # setplayGuideCommon
    "freekickDebug",
    ## player
    # contact
    "back_charge_forced_falldown",
    # freekick
    "longpassInplayUse",
    # matchup
    "delayAutoClose",
    ## team
    # basePosition
    "adjustGapDfLineAction",
    "adjustSetplay",
    "adjustSlideMoveSpeed",
    "changeDefenceNumberFromSituation",
    "dfAttackWidthForce",
    "dfUserPositionAdjustEnable",
    "isUseDashSituation",
    "umericalRelationDefenceLine",
    "offenceZposiAdjust",
    "onPassCourse",
    "returnControlSide",
    "slide",
    "slowDownFw",
    "teamToGroupAdjustEnable",
    "xposiRateCustom",
    # combination
    "useJson",
    # defenceCover
    "isNearPlayerAssign",
    # defenceMark
    "useCoverMoveSpeed",
    # pairAnime
    "pes15TestDecideTiming_enable",
    "highballEnable",
    "moveContact_firstAttackEnd_enable",
    "moveContact_pes15TestMoveContact_dropOut_enable",
    "moveContact_pes15TestMoveContact_tackleResultSetAnime",
    "stopContact_myGoalAngleEnable",
    "stopEnable",
    # pullAway
    "pullAwaySide",
    # spaceRun
    "backwardCurve",
    "shortConceptTest",
    "vitalSupportPrior",
    # subConcept
    "PossessionMfJoinDefenceLine",
    "ChangeTriangle",
    "CounterAfterGkCatch",
    "SideCounter",
    "FastCounter",
    "LongPassFlick",
    "LongPassLayOffAndToSide",
    "LongPassLayOffAndBreakthroughToDefenceLine",
    "LongPassLayOffAndShoot",
    "EarlyCross",
    "ForwardPassAndLayOff",
    "PassAndGoTriangle",
    "PenetrateInsideOneTwo",
    "SpaceRunToCenterForCreateSideSpace",
    "ToCenterDecoySide",
    "SpaceRunRelaySquarePass",
    "DisorderByOneTwo",
    "SideCrossRunning",
    "SideRunMakeSpace",
    "SpaceRunToCreateSpaceForOneTouchPass",
    "CreateSpaceOneTwo",
    "SideChangeToWeakSide",
    "SideOverlapAndSupport",
    "SideOverlapAndSpaceRun",
    "SideLongitudinalOneTwo",
    "SideInnerlap",
    "OneTwoPassFromSideToCenter",
    "OneTwoPassCutIn",
    "SupportBackOneTwo",
    "MoveDownMakeSpaceSide",
    "DiagonalPostPlay",
    "ForeCheckPress",
    "ForeCheckLineDown",
    "ForeCheckLineUp",
    "TransitionChase",
    "RetreatBlockCreate",
    "RetreatPressBack",
    "RetreatBlockForwardPass",
    "RetreatCrossBlockCreate",
    "ReverseSideCounter",
    "NetDefenceInducementIntoTheCenter",
    "NetDefenceCentralSurroundingPress",
    "PassCut",
    "SealOffInducementToTheSides",
    "SealOffSideSurroundingPress",
    "DoublePress",
]
one_byte_bools = [
    # basePosition
    "defenceFormationTest1",
    "defenceFormationTest2",
    "dfAdjustZ",
    "dfCoverAdjustX",
    "dfCoverEnable",
    "dfForceAverageZ",
    # pairAnime
    "moveEnable",
    "protectAuto1",
    "protectAuto2",
    "protectAuto3",
    "protectAuto4",
    "protectAuto5",
    "protectButton",
    "moveContact_pes15TestMoveContact_enable",
    "moveContact_pes15TestMoveContact_neutralEnd",
    # pullAway
    "eyeOff",
    "lastLine",
    "lastLineEnemy",
    "pullAway",
    # spaceRun
    "createPassCourse",
    "defenceGap",
    "inOut",
    "roundTest",
    # subConcept
    "subConcept_passRequest_all_off",
    "subConcept_passRequest_off",
]


def process_map(data: BytesIO, map_name: str, map_type: str, offset: int, pes_ver: int) -> dict[
    str, dict[int, float | int | bool]]:
    variables = {}
    try:
        with open(f"pes_ai/mappings/{pes_ver}/{map_type}/{map_name}.txt", "r") as f:
            file = f.read().split("\n")
    except FileNotFoundError:
        try:
            with open(f"pes_ai/mappings/generic/{map_type}/{map_name}.txt", "r") as f:
                file = f.read().split("\n")
        except FileNotFoundError:
            return variables

    i = 0
    for entry in file:
        if entry.startswith("#"):
            continue
        if "padding" in entry:
            entry_name = f"padding{i}"
            entry_off = 0
            i += 1
        else:
            entry_split = entry.split(" ")
            entry_name = entry_split[1]
            entry_off = int(entry_split[0])

        data.seek(offset + entry_off)
        variables[entry_name] = {"offset": entry_off, "value": None}
        if "padding" in entry_name:
            continue
        elif entry_name in bools:
            variables[entry_name]["value"] = bool(unpack("<i", data.read(4))[0])
        elif entry_name in one_byte_bools:
            variables[entry_name]["value"] = unpack("?", data.read(1))[0]
        else:
            variables[entry_name]["value"] = conv_from_bytes(data.read(4))
    return variables


def conv_from_bytes(byte_data: bytes) -> int | float:
    p = unpack("<i", byte_data)[0]
    if p > 10000 or p < 0:
        p = round(unpack("<f", byte_data)[0], 3)
    return p


def conv_to_bytes(value: int | float | bool | None) -> bytes:
    match type(value).__name__:
        case "int":
            return pack("<i", value)
        case "float":
            return pack("<f", value)
        case "bool":
            return pack("?", value)
        case _:
            return pack("x")
