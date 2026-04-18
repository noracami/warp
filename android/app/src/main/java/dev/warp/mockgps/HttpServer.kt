package dev.warp.mockgps

import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import fi.iki.elonen.NanoHTTPD
import org.json.JSONObject

class HttpServer(
    private val context: Context,
    port: Int = DEFAULT_PORT,
) : NanoHTTPD(port) {

    companion object {
        const val DEFAULT_PORT = 8080
        private const val TAG = "WarpHttpServer"
    }

    override fun serve(session: IHTTPSession): Response {
        return try {
            when {
                session.method == Method.OPTIONS -> cors(ok("{}"))
                session.method == Method.POST && session.uri == "/teleport" -> handleTeleport(session)
                session.method == Method.POST && session.uri == "/stop" -> handleStop()
                session.method == Method.GET && session.uri == "/status" -> handleStatus()
                else -> cors(
                    newFixedLengthResponse(
                        Response.Status.NOT_FOUND,
                        "application/json",
                        """{"error":"not found"}""",
                    ),
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "serve error", e)
            cors(
                newFixedLengthResponse(
                    Response.Status.INTERNAL_ERROR,
                    "application/json",
                    """{"error":${JSONObject.quote(e.message ?: "unknown")}}""",
                ),
            )
        }
    }

    private fun handleTeleport(session: IHTTPSession): Response {
        val body = HashMap<String, String>()
        session.parseBody(body)
        val raw = body["postData"]
        if (raw.isNullOrBlank()) {
            return cors(
                newFixedLengthResponse(
                    Response.Status.BAD_REQUEST,
                    "application/json",
                    """{"error":"missing body"}""",
                ),
            )
        }
        val obj = JSONObject(raw)
        val lat = obj.getDouble("lat")
        val lng = obj.getDouble("lng")

        val intent = Intent(context, MockLocationService::class.java).apply {
            action = MockLocationService.ACTION_START
            putExtra(MockLocationService.EXTRA_LAT, lat)
            putExtra(MockLocationService.EXTRA_LNG, lng)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent)
        } else {
            context.startService(intent)
        }
        Log.i(TAG, "teleport lat=$lat lng=$lng")

        return cors(ok("""{"ok":true,"lat":$lat,"lng":$lng}"""))
    }

    private fun handleStop(): Response {
        val intent = Intent(context, MockLocationService::class.java).apply {
            action = MockLocationService.ACTION_STOP
        }
        context.startService(intent)
        Log.i(TAG, "stop")
        return cors(ok("""{"ok":true}"""))
    }

    private fun handleStatus(): Response {
        val running = MockLocationService.isRunning
        val loc = MockLocationService.currentLocation
        val lastAt = MockLocationService.lastTeleportAt
        val json = JSONObject().apply {
            put("running", running)
            if (loc != null) {
                put("lat", loc.first)
                put("lng", loc.second)
            } else {
                put("lat", JSONObject.NULL)
                put("lng", JSONObject.NULL)
            }
            if (lastAt > 0) put("lastTeleportAt", lastAt) else put("lastTeleportAt", JSONObject.NULL)
        }
        return cors(ok(json.toString()))
    }

    private fun ok(body: String): Response =
        newFixedLengthResponse(Response.Status.OK, "application/json", body)

    private fun cors(response: Response): Response {
        response.addHeader("Access-Control-Allow-Origin", "*")
        response.addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.addHeader("Access-Control-Allow-Headers", "Content-Type")
        return response
    }
}
