"""Organization default and optional room style; the identity template stays unchanged."""
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .activity import record
from .drive import room_state
from .models import Activity


def workspace_style(organization):
    event = Activity.objects.filter(organization=organization, event_type='workspace.watermark.saved').first()
    return event.data['watermark_style'] if event else 'diagonal'


def effective_style(link):
    override = room_state(link.dataroom).get('watermark_style') if link.dataroom_id else None
    return override or workspace_style(link.organization)


class WorkspaceSettingsSerializer(serializers.Serializer):
    watermark_style = serializers.ChoiceField(choices=['diagonal', 'edge'])


class WorkspaceSettingsView(APIView):
    @extend_schema(responses=WorkspaceSettingsSerializer)
    def get(self, request):
        return Response({'watermark_style': workspace_style(request.user.organization)})

    @extend_schema(request=WorkspaceSettingsSerializer, responses=WorkspaceSettingsSerializer)
    def patch(self, request):
        serializer = WorkspaceSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record('workspace.watermark.saved', organization=request.user.organization,
               actor=request.user, data=serializer.validated_data)
        return Response(serializer.validated_data)


def edge_image(image, text):
    layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)
    size = max(8, int(image.width / 85))
    try:
        font = ImageFont.truetype(settings.WATERMARK_FONT_PATH, size=size)
    except (OSError, AttributeError):
        font = ImageFont.load_default(size=size)
    box = draw.textbbox((0, 0), text, font=font)
    # Render once and scale to fit; long identities keep every character and Copy ID.
    line = Image.new('RGBA', (max(1, box[2] - box[0]), max(1, box[3] - box[1])), (0, 0, 0, 0))
    ImageDraw.Draw(line).text((-box[0], -box[1]), text, font=font, fill=(60, 60, 60, 155))
    width = min(line.width, int(image.width * .94))
    fitted = line.resize((width, max(1, round(line.height * width / line.width))))
    layer.alpha_composite(fitted, ((image.width - width) // 2, image.height - fitted.height - max(6, image.height // 80)))
    result = Image.alpha_composite(image, layer)
    fitted.close(); line.close(); layer.close()
    return result


def edge_canvas(canvas, width, height, text, font):
    size = min(9, width / 85)
    text_width = canvas.stringWidth(text, font, size)
    size *= min(1, width * .94 / max(1, text_width))
    canvas.setFont(font, size)
    canvas.setFillColorRGB(.24, .24, .24, alpha=.6)
    canvas.drawCentredString(width / 2, max(6, height / 80), text)
