"""
Amazon Polly neural voice synthesis helper for AURI.
Provides text-to-speech using Vitória neural voice (pt-BR)
with SSML prosody controls and S3 audio storage.
"""

import io
import os
import uuid
import logging
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_VOICE = "Vitoria"
DEFAULT_ENGINE = "neural"
DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("AURI_AUDIO_BUCKET", "auri-audio")

# Available PT-BR voices
VOICES = {
    "vitoria": {"id": "Vitoria", "language": "pt-BR", "engine": "neural", "gender": "Female"},
    "camila": {"id": "Camila", "language": "pt-BR", "engine": "neural", "gender": "Female"},
    "ricardo": {"id": "Ricardo", "language": "pt-BR", "engine": "standard", "gender": "Male"},
    "ines": {"id": "Ines", "language": "pt-PT", "engine": "neural", "gender": "Female"},
}


# ---------------------------------------------------------------------------
# SSML Builder
# ---------------------------------------------------------------------------
def build_ssml(
    text: str,
    rate: str = "100%",
    pitch: str = "+0%",
    emphasis: Optional[str] = None,
    break_time: Optional[str] = None,
) -> str:
    """
    Build SSML markup for speech customization.

    Args:
        text: The text to speak.
        rate: Speech rate (e.g. '90%', '110%').
        pitch: Voice pitch (e.g. '+5%', '-5%').
        emphasis: Emphasis level ('strong', 'moderate', 'reduced') or None.
        break_time: Pause duration (e.g. '0.5s', '1s') or None.

    Returns:
        SSML-formatted string.
    """
    parts = ["<speak>"]

    if break_time:
        parts.append(f'<break time="{break_time}"/>')

    prosody_attrs = f'rate="{rate}" pitch="{pitch}"'
    if emphasis:
        parts.append(f'<prosody {prosody_attrs}>')
        parts.append(f'<emphasis level="{emphasis}">{text}</emphasis>')
        parts.append("</prosody>")
    else:
        parts.append(f'<prosody {prosody_attrs}>{text}</prosody>')

    parts.append("</speak>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Speech synthesis
# ---------------------------------------------------------------------------
def synthesize_speech(
    text: str,
    voice_id: str = DEFAULT_VOICE,
    engine: str = DEFAULT_ENGINE,
    output_format: str = "mp3",
    use_ssml: bool = False,
) -> bytes:
    """
    Synthesize speech using Amazon Polly.

    Args:
        text: Text or SSML to synthesize.
        voice_id: Polly voice ID.
        engine: 'neural' or 'standard'.
        output_format: 'mp3', 'ogg_vorbis', or 'pcm'.
        use_ssml: Whether text is SSML markup.

    Returns:
        Audio bytes in the specified format.
    """
    client = boto3.client("polly", region_name=DEFAULT_REGION)

    params = {
        "Text": text,
        "OutputFormat": output_format,
        "VoiceId": voice_id,
        "Engine": engine,
    }
    if use_ssml:
        params["TextType"] = "ssml"

    response = client.synthesize_speech(**params)
    audio_stream = response["AudioStream"].read()
    logger.info(
        "Synthesized %d bytes of audio (voice=%s, engine=%s)",
        len(audio_stream),
        voice_id,
        engine,
    )
    return audio_stream


def upload_audio_to_s3(
    audio_bytes: bytes,
    bucket: str = S3_BUCKET,
    content_type: str = "audio/mpeg",
) -> str:
    """
    Upload audio bytes to S3 and return a presigned URL.

    Args:
        audio_bytes: The audio data.
        bucket: S3 bucket name.
        content_type: MIME type of the audio.

    Returns:
        Presigned URL for the uploaded audio (valid 1 hour).
    """
    s3 = boto3.client("s3", region_name=DEFAULT_REGION)
    key = f"audio/{uuid.uuid4().hex}.mp3"

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=audio_bytes,
        ContentType=content_type,
    )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600,
    )
    logger.info("Uploaded audio to s3://%s/%s", bucket, key)
    return url


def speak_with_polly(
    text: str,
    voice_id: str = DEFAULT_VOICE,
    rate: str = "95%",
    pitch: str = "+3%",
) -> str:
    """
    Full pipeline: build SSML, synthesize with Polly, upload to S3,
    and return SSML with <audio> tag for Alexa.

    Args:
        text: The text to speak.
        voice_id: Polly voice.
        rate: Speech rate.
        pitch: Voice pitch.

    Returns:
        SSML string with embedded audio URL for Alexa response.
    """
    ssml_text = build_ssml(text, rate=rate, pitch=pitch)
    audio_bytes = synthesize_speech(ssml_text, voice_id=voice_id, use_ssml=True)
    audio_url = upload_audio_to_s3(audio_bytes)
    return f'<speak><audio src="{audio_url}"/></speak>'
