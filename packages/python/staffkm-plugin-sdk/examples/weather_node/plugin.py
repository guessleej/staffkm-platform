"""範例 plugin: 查天氣 node。"""
from staffkm_plugin_sdk.base import BaseNode, PluginContext


class WeatherNode(BaseNode):
    node_type = "weather_lookup"

    async def execute(self, config: dict, ctx: PluginContext, inputs: dict) -> dict:
        """config: { city, output_variable }"""
        import httpx

        city = config.get("city") or inputs.get("user_input", "Taipei")
        out_var = config.get("output_variable", "weather")
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"https://wttr.in/{city}?format=3")
                return {out_var: r.text.strip()}
        except Exception as e:
            return {out_var: f"error: {e}"}
