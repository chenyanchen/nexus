import asyncio

from langchain.agents import create_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client


async def create_mcp_stdio_client():
    server_parameters = StdioServerParameters(
        command="npx",
        args=["@playwright/mcp@latest"],
    )
    async with stdio_client(server=server_parameters) as (reader, writer):
        async with ClientSession(read_stream=reader, write_stream=writer) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_agent(
                model="deepseek-chat",
                tools=tools,
                system_prompt="You are helpful assistant",
                debug=True,
            )
            resp = await agent.ainvoke(
                input={
                    "messages": [
                        (
                            "user",
                            """目标：

- 使用 Playwright 访问各国新闻媒体网址
- 查看首页是否有关于{委内瑞拉总统被美国逮捕}的新闻
- 提取并总结各媒体对于{委内瑞拉总统被美国逮捕}的核心看法，并整理为 markdown 表格

表格示例：

| 国家/组织  | 媒体名称     | 文章                                                                                                                 | 核心观点                                               |
| ---------- | ------------ | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **联合国** | 联合国新闻网 | [US actions in Venezuela ‘constitute a dangerous precedent’: Guterres](https://news.un.org/en/story/2026/01/1166698) | the rules of international law have not been respected |

### 全球媒体网站汇总表

| 国家/组织      | 媒体名称                      | 官方网址                                                             |
| -------------- | ----------------------------- | -------------------------------------------------------------------- |
| **联合国**     | 联合国新闻网                  | [https://news.un.org/zh/](https://news.un.org/zh/)                   |
|                | 联合国数字图书馆              | [https://digitallibrary.un.org/](https://digitallibrary.un.org/)     |
| **美国**       | 美国有线电视新闻网 (CNN)      | [https://edition.cnn.com/](https://edition.cnn.com/)                 |
|                | 洛杉矶时报                    | [https://www.latimes.com/](https://www.latimes.com/)                 |
|                | 美联社 (AP)                   | [https://www.ap.org/](https://www.ap.org/)                           |
| **俄罗斯**     | 今日俄罗斯 (RT)               | [https://www.rt.com/](https://www.rt.com/)                           |
|                | 塔斯社 (TASS)                 | [https://tass.com/](https://tass.com/)                               |
| **德国**       | 时代周报 (Die Zeit)           | [https://www.zeit.de/index](https://www.zeit.de/index)               |
| **英国**       | 每日电讯报                    | [https://www.telegraph.co.uk/](https://www.telegraph.co.uk/)         |
| **法国**       | France 24                     | [https://www.france24.com/en/](https://www.france24.com/en/)         |
| **日本**       | 日本公共媒体 (NHK)            | [https://www3.nhk.or.jp/news/](https://www3.nhk.or.jp/news/)         |
|                | 雅虎日本新闻网                | [https://news.yahoo.co.jp/](https://news.yahoo.co.jp/)               |
| **韩国**       | 韩联社 (Yonhap)               | [https://en.yna.co.kr/](https://en.yna.co.kr/)                       |
|                | 韩国时报                      | [https://www.koreatimes.co.kr/](https://www.koreatimes.co.kr/)       |
| **意大利**     | 晚邮报 (Corriere della Sera)  | [https://www.corriere.it/](https://www.corriere.it/)                 |
|                | 安莎社 (ANSA)                 | [https://www.ansa.it/english](https://www.ansa.it/english)           |
| **加拿大**     | CTV News                      | [https://www.ctvnews.ca/](https://www.ctvnews.ca/)                   |
|                | Global News                   | [https://globalnews.ca/](https://globalnews.ca/)                     |
| **巴西**       | 圣保罗页报 (Folha de S.Paulo) | [https://www.folha.uol.com.br/](https://www.folha.uol.com.br/)       |
| **土耳其**     | 自由报 (Hürriyet)             | [https://www.hurriyet.com.tr/](https://www.hurriyet.com.tr/)         |
|                | 米利耶特报 (Milliyet)         | [https://www.milliyet.com.tr/](https://www.milliyet.com.tr/)         |
| **沙特阿拉伯** | 阿拉伯新闻 (Arab News)        | [https://www.arabnews.com/](https://www.arabnews.com/)               |
|                | 沙特公报 (Saudi Gazette)      | [https://saudigazette.com.sa/](https://saudigazette.com.sa/)         |
| **巴基斯坦**   | Samaa TV                      | [https://www.samaa.tv/](https://www.samaa.tv/)                       |
|                | ARY News                      | [https://arynews.tv/](https://arynews.tv/)                           |
| **以色列**     | 以色列时报                    | [https://www.timesofisrael.com/](https://www.timesofisrael.com/)     |
|                | 国土报 (Haaretz)              | [https://www.haaretz.com/](https://www.haaretz.com/)                 |
| **伊朗**       | 伊朗通讯社 (IRNA)             | [https://en.irna.ir/](https://en.irna.ir/)                           |
|                | Press TV                      | [https://www.presstv.ir/](https://www.presstv.ir/)                   |
| **南非**       | 邮报与卫报 (Mail & Guardian)  | [https://mg.co.za/](https://mg.co.za/)                               |
| **阿联酋**     | 海湾新闻 (Gulf News)          | [https://gulfnews.com/](https://gulfnews.com/)                       |
|                | 国家报 (The National)         | [https://www.thenationalnews.com/](https://www.thenationalnews.com/) |
| **新加坡**     | Mothership.SG                 | [https://mothership.sg](https://mothership.sg)                       |
| **乌克兰**     | 乌克兰国家通讯社 (Ukrinform)  | [https://www.ukrinform.net/](https://www.ukrinform.net/)             |
|                | 基辅独立报                    | [https://kyivindependent.com/](https://kyivindependent.com/)         |
| **波兰**       | 华沙之声                      | [https://www.warsawvoice.pl/](https://www.warsawvoice.pl/)           |
|                | 共和国报 (Rzeczpospolita)     | [https://www.rp.pl/](https://www.rp.pl/)                             |
| **立陶宛**     | Delfi                         | [https://www.delfi.lt/](https://www.delfi.lt/)                       |
|                | Lrytas.lt                     | [https://www.lrytas.lt/english](https://www.lrytas.lt/english)       |
| **马来西亚**   | 星报 (The Star)               | [https://www.thestar.com.my/](https://www.thestar.com.my/)           |
| **印度尼西亚** | 安塔拉通讯社 (Antara News)    | [https://en.antaranews.com/](https://en.antaranews.com/)             |
| **越南**       | 越南新闻 (Vietnam News)       | [https://vietnamnews.vn/](https://vietnamnews.vn/)                   |
|                | VnExpress International       | [https://e.vnexpress.net/](https://e.vnexpress.net/)                 |
| **埃及**       | 金字塔报                      | [https://english.ahram.org.eg/](https://english.ahram.org.eg/)       |
| **肯尼亚**     | 民族日报 (Daily Nation)       | [https://nation.africa/kenya](https://nation.africa/kenya)           |
|                | 标准报 (The Standard)         | [https://www.standardmedia.co.ke/](https://www.standardmedia.co.ke/) |
| **尼日利亚**   | 高级时报 (Premium Times)      | [https://www.premiumtimesng.com/](https://www.premiumtimesng.com/)   |
|                | 卫报 (The Guardian Nigeria)   | [https://guardian.ng/](https://guardian.ng/)                         |
""",
                        )
                    ]
                }
            )
            print(resp)


async def main():
    await create_mcp_stdio_client()


if __name__ == "__main__":
    asyncio.run(main())
