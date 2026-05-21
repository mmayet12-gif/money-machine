from .s1_youtube_longform import build_stream_units as s1_build
from .s2_youtube_shorts import build_stream_units as s2_build
from .s3_tiktok_reels import build_stream_units as s3_build
from .s4_seo_blogs import build_stream_units as s4_build
from .s5_email_newsletter import build_stream_units as s5_build
from .s6_affiliate_assets import build_stream_units as s6_build
from .s7_digital_product import build_stream_units as s7_build
from .s8_distribution_pack import build_stream_units as s8_build

STREAM_BUILDERS = {
    "S1": s1_build,
    "S2": s2_build,
    "S3": s3_build,
    "S4": s4_build,
    "S5": s5_build,
    "S6": s6_build,
    "S7": s7_build,
    "S8": s8_build,
}
