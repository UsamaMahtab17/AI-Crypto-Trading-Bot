from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI, BackgroundTasks, HTTPException
import asyncio
from typing import Optional
from utils.utils import execute_strategy
from datetime import datetime
import logging
from socket_manager import ws_manager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect,WebSocketException,Query
from typing import List, Dict
from models.schemas import StartBotRequest


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global variables for managing tasks
active_tasks = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, strategy_id: str = Query(...)):
    try:
        # Connect using conversation ID
        await ws_manager.connect(strategy_id, websocket)
        print(f"Client connected: {strategy_id}") 
        
        while True:
            try:
                # Keep the connection alive by waiting for incoming messages or a disconnection
                await websocket.receive_text()  # You can ignore the received text if not needed
            except WebSocketDisconnect:
                print(f"Client disconnected: {strategy_id}")
                await ws_manager.disconnect(strategy_id)
                break
        # while True:
        #     try:
        #         # Send message to the frontend periodically
        #         # await ws_manager.send_message(strategy_id, f"Hello from server to {strategy_id}")
        #         # await asyncio.sleep(5)  # Adjust the interval for sending messages
        #     except WebSocketDisconnect:
        #         print(f"Client disconnected: {strategy_id}")
        #         await ws_manager.disconnect(strategy_id)
        #         break
        #     except Exception as e:
        #         print(f"Error sending message: {e}")
        #         break

    except WebSocketException as e:
        # Handle WebSocket-related exceptions like duplicate conversation IDs
        print(f"Client disconnected: {strategy_id}")
        await ws_manager.disconnect(strategy_id)
        print(f"WebSocket Exception: {e}")

    except Exception as e:
        print(f"Client disconnected: {strategy_id}")
        await ws_manager.disconnect(strategy_id)
        print(f"WebSocket Error: {e}")

    # finally:
    #     # Ensure disconnection happens even on error
    #     await ws_manager.disconnect(strategy_id)
    
        
@app.post("/start")
async def start_bot(
    request: StartBotRequest
    # pair: str,
    # strategy_id: str,
    # strategy: str = "MACD",
    # stop_loss: Optional[float] = None,
    # take_profit: Optional[float] = None,
    # params: Optional[Dict[str, float]] = None
):
    
    """
    Start a bot for a specific trading pair using a chosen strategy.\n
    Args:\n
        pair (str): Trading pair, e.g., "BTC/USD".\n
        strategy_id (str): Unique identifier for the strategy instance.\n
        strategy (str): Trading strategy to use (e.g., "MACD", "RSI").\n
        stop_loss (float, optional): Stop-loss level.\n
        take_profit (float, optional): Take-profit level.\n
        params (dict, optional): Additional parameters according to the chosen strategy.\n
            For MACD: short_window, long_window, signal_window\n
            For RSI: period\n
            For EMA: short_period, long_period\n
            For Bollinger Bands: window, multiplier\n

    """

    if request.pair in active_tasks:
        logger.warning(f"Attempted to start bot for {request.pair}, but it's already running.")
        raise HTTPException(status_code=400, detail=f"Bot already running for pair {request.pair}.")
    
        # Validate strategy parameters
    if request.strategy == "MACD":
        required_params = ["short_window", "long_window", "signal_window"]
    elif request.strategy == "RSI":
        required_params = ["period"]
    elif request.strategy == "EMA":
        required_params = ["short_period", "long_period"]
    elif request.strategy == "Bollinger Bands":
        required_params = ["window", "multiplier"]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")
                            
    # Check if all required parameters are provided
    if request.params is None:
        raise HTTPException(status_code=400, detail=f"Missing parameters for strategy {request.strategy}")
    missing_params = [param for param in required_params if getattr(request.params, param, None) is None]
    if missing_params:
        raise HTTPException(status_code=400, detail=f"Missing parameter(s): {', '.join(missing_params)} for strategy {request.strategy}")
    

    logger.info(f"Starting bot for pair {request.pair} with strategy {request.strategy}")
    params = request.params.dict()  # Convert Pydantic model to dictionary
    task = asyncio.create_task(execute_strategy(request.pair, request.strategy,request.strategy_id, request.stop_loss, request.take_profit, **params))
    active_tasks[request.pair] = {
        "task": task,
        "strategy": request.strategy,
        "start_time": datetime.now(),
    }
    return {"message": f"Bot started for pair {request.pair} with strategy {request.strategy}"}



@app.post("/stop")
async def stop_bot(pair: str):
    if pair not in active_tasks:
        logger.warning(f"Attempted to stop bot for {pair}, but no bot is running.")
        raise HTTPException(status_code=404, detail=f"No bot running for pair {pair}.")

    logger.info(f"Stopping bot for pair {pair}")
    task = active_tasks[pair]["task"]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info(f"Bot for pair {pair} successfully stopped.")
    del active_tasks[pair]
    return {"message": f"Bot for pair {pair} stopped."}

@app.get("/status")
async def get_status():
    status = {}
    for pair, info in active_tasks.items():
        task = info["task"]
        if task.done():
            state = "done"
        elif task.cancelled():
            state = "cancelled"
        else:
            state = "running"

        status[pair] = {
            "state": state,
            "strategy": info["strategy"],
            "start_time": info["start_time"].isoformat(),
        }

    return {"active_bots": status}

