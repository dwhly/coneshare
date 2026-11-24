from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('dealroom', '0005_boardroom')]
    operations = [
        migrations.AddField(model_name='boardroom', name='staged_import',
                            field=models.CharField(max_length=36, blank=True, default='')),
        migrations.CreateModel(name='RoomCommandReceipt', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('board_id', models.CharField(max_length=100)),
            ('command_key', models.CharField(max_length=200)),
            ('actor', models.CharField(max_length=254)), ('via', models.CharField(max_length=32)),
            ('operation', models.CharField(max_length=32)), ('payload_sha256', models.CharField(max_length=64)),
            ('approved_manifest', models.JSONField(null=True, blank=True)), ('result', models.JSONField(default=dict)),
            ('room', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='datarooms.dataroom')),
            ('approval_key', models.CharField(max_length=200, blank=True)),
            ('import_id', models.CharField(max_length=36)), ('client_item_id', models.CharField(max_length=128, blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.AddConstraint(model_name='roomcommandreceipt', constraint=models.UniqueConstraint(fields=['board_id', 'command_key'], name='room_command_key')),
        migrations.AddConstraint(model_name='roomcommandreceipt', constraint=models.UniqueConstraint(fields=['board_id', 'import_id', 'operation', 'client_item_id'], name='room_import_step')),
    ]
