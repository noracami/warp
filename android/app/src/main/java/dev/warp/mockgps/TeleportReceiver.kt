package dev.warp.mockgps

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

class TeleportReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            "dev.warp.mockgps.TELEPORT" -> {
                val lat = readDouble(intent, "lat")
                val lng = readDouble(intent, "lng")
                if (lat == null || lng == null) {
                    Log.w(TAG, "TELEPORT 缺少 lat/lng：extras=${intent.extras?.keySet()}")
                    return
                }
                Log.i(TAG, "TELEPORT lat=$lat lng=$lng")
                val svc = Intent(context, MockLocationService::class.java).apply {
                    action = MockLocationService.ACTION_START
                    putExtra(MockLocationService.EXTRA_LAT, lat)
                    putExtra(MockLocationService.EXTRA_LNG, lng)
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(svc)
                } else {
                    context.startService(svc)
                }
            }
            "dev.warp.mockgps.STOP" -> {
                Log.i(TAG, "STOP")
                val svc = Intent(context, MockLocationService::class.java).apply {
                    action = MockLocationService.ACTION_STOP
                }
                context.startService(svc)
            }
        }
    }

    private fun readDouble(intent: Intent, key: String): Double? {
        val extras = intent.extras ?: return null
        if (!extras.containsKey(key)) return null
        return when (val v = extras.get(key)) {
            is Double -> v
            is Float -> v.toDouble()
            is Int -> v.toDouble()
            is Long -> v.toDouble()
            is String -> v.toDoubleOrNull()
            else -> null
        }
    }

    companion object {
        private const val TAG = "TeleportReceiver"
    }
}
