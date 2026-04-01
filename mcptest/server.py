import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

# 创建Server实例，名字叫"weather-server"
app = Server("weather-server")

import aiohttp
from mcp.types import CallToolResult, TextContent

# 你的OpenWeatherMap API Key，建议从环境变量读取
API_KEY = "8467f0accbb11504bc1ab78a21d64ce7"

@app.call_tool()
async def get_weather(city: str) -> CallToolResult:
    """根据城市名称查询当前天气情况
    
    Args:
        city: 城市名称，例如"Beijing"或"上海"
    
    Returns:
        返回该城市的当前天气信息，包括温度和天气状况。
    """
    # 构建请求URL
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    
    # 错误处理与超时控制
    try:
        async with aiohttp.ClientSession() as session:
            # 设置10秒超时
            async with asyncio.timeout(10):
                async with session.get(url) as response:
                    # 检查HTTP状态码是否成功
                    response.raise_for_status()
                    data = await response.json()
                    
                    # 解析返回的JSON数据
                    temperature = data['main']['temp']
                    description = data['weather'][0]['description']
                    result_text = f"{city}的当前天气：温度{temperature}℃，{description}"
                    
                    return CallToolResult(content=[TextContent(type="text", text=result_text)], isError=False)
                    
    except asyncio.TimeoutError:
        return CallToolResult(content=[TextContent(type="text", text="天气请求超时，请稍后重试")], isError=True)
    except aiohttp.ClientResponseError as e:
        return CallToolResult(content=[TextContent(type="text", text=f"HTTP错误: {e.status} - {e.message}")], isError=True)
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"获取天气信息时发生错误: {str(e)}")], isError=True)

# 此处将注册我们的工具和资源
async def main():
    # 使用stdio传输层，这是与Claude等客户端通信的标准方式
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())