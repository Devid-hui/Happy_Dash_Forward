extends AudioStreamPlayer3D
static var warning_stream: AudioStreamWAV

func _ready() -> void:
	name = "ChargeWarning"
	add_to_group("procedural_audio")
	max_distance = 38.0
	unit_size = 6.0
	volume_db = -14.0
	if warning_stream == null:
		# 自制非循环短尖叫：扫频、谐波和抖动，独立于雨声及世界脚本。
		var rate := 22050
		var samples := int(rate * 1.05)
		var data := PackedByteArray()
		data.resize(samples * 2)
		var phase := 0.0
		for i in range(samples):
			var t := float(i) / rate
			var envelope := sin(PI * t / 1.05) * minf(1.0,t * 30.0)
			phase += TAU * (430.0 + 540.0 * sin(PI*t/1.05) + 45.0*sin(t*91.0)) / rate
			var sample := envelope * (.52*sin(phase)+.24*sin(phase*2.03)+.14*sin(phase*3.11))
			data.encode_s16(i*2,int(clampf(sample,-1.0,1.0)*22000))
		warning_stream = AudioStreamWAV.new()
		warning_stream.format = AudioStreamWAV.FORMAT_16_BITS
		warning_stream.mix_rate = rate
		warning_stream.data = data
	stream = warning_stream

func _exit_tree() -> void:
	stop()
	stream = null
