#from typing import Union

from fastapi import FastAPI, Query, HTTPException

from utili import load_model, porphet_predict, convert_json, product_estimate_price, validate_arguments, plot_predictions

description = """
This API service is used to forecast product price given the contributing materials that form the final product.

You can provide a variable "months" to set the forecasting period

forecast starts from 2/2023, as it is the last timestamp sample in the training set

## Details on data

"st37": "Weight of ST37 in KG",
"p_st37": "Spot price of ST37",
"p_high_carbon": "Spot price of High Carbon",
"alu": "Weight of Alu in KG",
"labour": "Labor hours",
"high_carbon": "Weight of High Carbon in KG",
"medium_carbon": "Weight of Medium Carbon in KG",
"p_medium_carbon": "Spot Price of Medium Carbon",
"p_nodular_cast_iron": "Spot Price of Nodular Cast Iron",
"nodular_cast_iron": "Weight of Nodular Cast Iron in KG",
"grey_cast_iron": "Weight of Grey Cast Iron in KG",
"p_grey_cast_iron": "Spot Price of Grey Cast Iron",
"nonalloy_cast": "Weight of Nonalloy Cast in KG",
"p_nonalloy_cast": "Spot Price of Nonalloy Cast",
"months": "Forecasting period in months (default is 24 months if argument not provided)"

"""

app = FastAPI(title="Price forecasting service",
    description=description)

@app.get("/status")
def read_root():
    return {"Status": "Service Running"}

@app.get("/help")
def get_help():
    help_info = {
        "st37": "Weight of ST37 in KG",
        "high_carbon": "Weight of High Carbon in KG",
        "alu": "Weight of Alu in KG",
        "nodular_cast_iron": "Weight of Nodular Cast Iron in KG",
        "copper": "Weight of Copper in KG",
        "medium_carbon": "Weight of Medium Carbon in KG",
        "nonalloy_cast": "Weight of Nonalloy Cast in KG",
        "grey_cast_iron": "Weight of Grey Cast Iron in KG",
        "p_st37": "Spot price of ST37",
        "p_high_carbon": "Spot price of High Carbon",
        "p_medium_carbon": "Spot Price of Medium Carbon",
        "p_nodular_cast_iron": "Spot Price of Nodular Cast Iron",
        "p_grey_cast_iron": "Spot Price of Grey Cast Iron",
        "p_nonalloy_cast": "Spot Price of Nonalloy Cast",
        "labour": "Labor hours",
        "months": "Forecasting period in months (default is 24 months if argument not provided)"
    }
    return help_info

@app.get("/calculate/")
def calculate(
    st37: float = Query(None, title="ST37", description="Weight of ST37"),
    copper: float = Query(None, title="Copper", description="Weight of Copper"),
    p_st37: float = Query(None, title = "spot_ST37", description = "spot price of ST37"),
    p_high_carbon: float = Query(None, title = "spot_High_Carbon", description = "spot price of High Carbon"),
    alu: float = Query(None, title="Alu", description="Weight of Alu"),
    labour: float = Query(None, title="Labour", description="Labor hours"),
    high_carbon: float = Query(None, title="high_carbon", description="Weight of High Carbon"),
    medium_carbon: float = Query(None, title="medium_carbon", description="Weight of Medium Carbon"),
    p_medium_carbon: float = Query(None, title = "Spot_Medium_Carbon", description = "Spot Price of Medium Carbon"),
    p_nodular_cast_iron: float = Query(None, title = "Spot_Nodular_Iron", description = "Spot Price of Nodular Cast Iron"),
    nodular_cast_iron: float = Query(None, title="nodular_cast_iron", description="Weight of Nodular Cast Iron"),
    grey_cast_iron: float = Query(None, title="grey_cast_iron", description="Weight of Grey Cast Iron"),
    p_grey_cast_iron: float = Query(None, title = "Spot_grey_cast_iron", description = "Spot Price of Grey_Cast_Iron"),
    nonalloy_cast: float = Query(None, title="nonalloy_cast", description="Weight of Nonalloy Cast"),
    p_nonalloy_cast: float = Query(None, title = "Spot_nonalloy_cast", description = "Spot Price of Nonalloy Cast"),
    months: int = Query(None, title = "length of prediction time", description = "Forecasting period in months")
):

    materials = {}
    # Check and parse ST37 material
    if st37 is not None:
        materials["st37"] = st37

    # Check and parse Copper material
    if copper is not None:
        materials["copper"] = copper

    if p_st37 is not None:
        materials["p_st37"] = p_st37
    # Check and parse Alu material
    if alu is not None:
        materials["alu"] = alu

    # Check and parse labor hours
    if labour is not None:
        materials["labour_hours"] = labour

    # check and parse high carbon
    if high_carbon is not None:
    	materials["high_carbon"] = high_carbon

    if p_high_carbon is not None:
        materials["p_high_carbon"] = p_high_carbon

    # check and parse grey cast iron
    if grey_cast_iron is not None:
        materials["grey_cast_iron"] = grey_cast_iron
    if p_grey_cast_iron is not None:
        materials["p_grey_cast_iron"] = p_grey_cast_iron

    # check and parse nodular cast iron
    if nodular_cast_iron is not None:
        materials["nodular_cast_iron"] = nodular_cast_iron
    if p_nodular_cast_iron is not None:
        materials["p_nodular_cast_iron"] = p_nodular_cast_iron
    # check and parse nonalloy cast
    if nonalloy_cast is not None:
        materials["nonalloy_cast"] = nonalloy_cast
    if p_nonalloy_cast is not None:
        materials["p_nonalloy_cast"] = p_nonalloy_cast
    # check and parse medium carbon
    if medium_carbon is not None:
        materials["medium_carbon"] = medium_carbon
    if p_medium_carbon is not None:
        materials["p_medium_carbon"] = p_medium_carbon
    # check and parse months
    if months is not None:
       materials["months"] = months
    validate_arguments(materials)
    predictions = product_estimate_price(materials)
    return predictions

@app.get("/plot/")
def plot(
    st37: float = Query(None, title="ST37", description="Weight of ST37"),
    copper: float = Query(None, title="Copper", description="Weight of Copper"),
    p_st37: float = Query(None, title = "spot_ST37", description = "spot price of ST37"),
    p_high_carbon: float = Query(None, title = "spot_High_Carbon", description = "spot price of High Carbon"),
    alu: float = Query(None, title="Alu", description="Weight of Alu"),
    labour: float = Query(None, title="Labour", description="Labor hours"),
    high_carbon: float = Query(None, title="high_carbon", description="Weight of High Carbon"),
    medium_carbon: float = Query(None, title="medium_carbon", description="Weight of Medium Carbon"),
    p_medium_carbon: float = Query(None, title = "Spot_Medium_Carbon", description = "Spot Price of Medium Carbon"),
    p_nodular_cast_iron: float = Query(None, title = "Spot_Nodular_Iron", description = "Spot Price of Nodular Cast Iron"),
    nodular_cast_iron: float = Query(None, title="nodular_cast_iron", description="Weight of Nodular Cast Iron"),
    grey_cast_iron: float = Query(None, title="grey_cast_iron", description="Weight of Grey Cast Iron"),
    p_grey_cast_iron: float = Query(None, title = "Spot_grey_cast_iron", description = "Spot Price of Grey_Cast_Iron"),
    nonalloy_cast: float = Query(None, title="nonalloy_cast", description="Weight of Nonalloy Cast"),
    p_nonalloy_cast: float = Query(None, title = "Spot_nonalloy_cast", description = "Spot Price of Nonalloy Cast"),
    months: int = Query(None, title = "length of prediction time", description = "Forecasting period in months")
):
    # Get the predicted values
    materials = {}
    if st37 is not None:
        materials["st37"] = st37
    if copper is not None:
        materials["copper"] = copper
    if p_st37 is not None:
        materials["p_st37"] = p_st37
    if alu is not None:
        materials["alu"] = alu
    if labour is not None:
        materials["labour_hours"] = labour
    if high_carbon is not None:
        materials["high_carbon"] = high_carbon
    if p_high_carbon is not None:
        materials["p_high_carbon"] = p_high_carbon
    if grey_cast_iron is not None:
        materials["grey_cast_iron"] = grey_cast_iron
    if p_grey_cast_iron is not None:
        materials["p_grey_cast_iron"] = p_grey_cast_iron
    if nodular_cast_iron is not None:
        materials["nodular_cast_iron"] = nodular_cast_iron
    if p_nodular_cast_iron is not None:
        materials["p_nodular_cast_iron"] = p_nodular_cast_iron
    if nonalloy_cast is not None:
        materials["nonalloy_cast"] = nonalloy_cast
    if p_nonalloy_cast is not None:
        materials["p_nonalloy_cast"] = p_nonalloy_cast
    if medium_carbon is not None:
        materials["medium_carbon"] = medium_carbon
    if p_medium_carbon is not None:
        materials["p_medium_carbon"] = p_medium_carbon
    if months is not None:
       materials["months"] = months

    # Validate the arguments
    validate_arguments(materials)
    
    # Get predictions
    predictions = product_estimate_price(materials)
    
    # Plot the predictions
    return plot_predictions(predictions)
