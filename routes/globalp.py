from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse


from utils.sp_handler import Search_suggestions_spotify
global_router = APIRouter()

@global_router.post('/suggestions')
async def search_suggestions(request: Request):
    try:
        # Fetch the JSON data from the request
        data = await request.json()
        search = data.get("query", "").strip()
        
        # Handle empty query
        if not search:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "Query is empty", "suggestions": []}
            )
        
        # Process search and return results
        result = Search_suggestions_spotify(search)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "suggestions": result}
        )
        
    except Exception as e:
        print(f"Error in /search/suggestions endpoint: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"An unexpected error occurred: {str(e)}", "suggestions": []}
        )
