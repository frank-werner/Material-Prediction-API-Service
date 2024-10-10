import pickle
import json
import neuralprophet
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from fastapi.responses import StreamingResponse
from fastapi import HTTPException

def plot_predictions(predictions):
    """
    Plot the predictions over time.

    Args:
        predictions (list): A list of dictionaries with 'ds' and 'total_product_value' keys.
    """
    # Extract dates and values from the predictions list
    dates = [entry['ds'] for entry in predictions]
    values = [entry['total_product_value'] for entry in predictions]
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(dates, values, marker='o', color='b')
    plt.title('Product Price Forecast')
    plt.xlabel('Date')
    plt.ylabel('Total Product Value')
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    
    # Save plot to an in-memory buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Return the image as a StreamingResponse
    return StreamingResponse(buf, media_type="image/png")


def validate_arguments(args):
    # Define non-material keys
    non_material_keys = {"labour_hours", "alu", "months","copper"}
    # Collect spot price and material weight keys, excluding non-materials
    spot_price_keys = [key for key in args if key.startswith('p_') and key[2:] not in non_material_keys]
    material_keys = [key for key in args if key not in non_material_keys and not key.startswith('p_')]
    print(material_keys)
    # Check if all spot prices have corresponding material weights
    for spot_price_key in spot_price_keys:
        material_key = spot_price_key[2:]  # Strip 'p_' to get the material key
        if material_key not in material_keys:
            raise HTTPException(status_code=400, detail=f"Weight for {material_key} is missing while its spot price is provided.")

    # If any material has a spot price, all others must have spot prices if they exist
    if spot_price_keys:
        for material_key in material_keys:
            if f"p_{material_key}" not in spot_price_keys and args[material_key] is not None:
                raise HTTPException(status_code=400, detail=f"Spot price for {material_key} is missing while other materials have spot prices.")

def load_model(name):
    model_path = 'models' + '/' + name + '.pkl'
    with open(model_path, 'rb') as f:
        m = pickle.load(f)
    return m

def adjust_spot_price(full_projected_values, spot_price):
    # assume spot date = 1/2023
    target_date = '2023-01-01'
    target_yhat1 = full_projected_values.loc[full_projected_values['ds'] == target_date, 'yhat1'].values[0]
    full_projected_values['recalculated_yhat1'] = (full_projected_values['yhat1'] / target_yhat1) * spot_price
    # Replace the original yhat1 column with the recalculated values
    full_projected_values['yhat1'] = full_projected_values['recalculated_yhat1']

    # Drop the recalculated_yhat1 column as it's no longer needed
    full_projected_values.drop(columns=['recalculated_yhat1'], inplace=True)
    return full_projected_values

def porphet_predict(model_name, csv_file_name, forecasting_period = 24):
    prophet_model = load_model(model_name)
    prophet_model.restore_trainer()
    data_file_path = 'data' + '/' + csv_file_name + '.csv'
    data_file = pd.read_csv(data_file_path)
    df_future = prophet_model.make_future_dataframe(data_file, periods=forecasting_period, n_historic_predictions=True)
    # Predict the future
    forecast = prophet_model.predict(df_future)

    # get the months predicted values from yhat1
    return forecast[['ds', 'yhat1']].tail(forecasting_period), forecast[['ds', 'yhat1']]

def product_estimate_price(args):
    total_product_values = 0

    if 'months' in args:
        forecasting_period = args['months']
    else:
        # Default period would be 24 months (2 years)
        forecasting_period = 24
        
    # Initialize an empty DataFrame to collect the 'ds' and 'yhat1' values
    #total_product_df = pd.DataFrame()
    

    if 'copper' in args:
        # use months as length of predicted values in the future
        copper_predicted_values, copper_full_projected_values = porphet_predict(model_name='higher_copper',
                                                                          csv_file_name='copper',
                                                                          forecasting_period = forecasting_period)
        copper_predicted_values.reset_index(drop= True, inplace = True)
        copper_predicted_values['yhat1'] *= args['copper']
        total_product_values += copper_predicted_values['yhat1'].squeeze()
    # Predict aluminum price if alu_weight is provided
    if 'alu' in args:
        # use months as length of predicted values in the future
        alu_predicted_values, alu_full_projected_values = porphet_predict(model_name='Aluminum_prophet',
                                                                          csv_file_name='aluminum',
                                                                          forecasting_period = forecasting_period)
        alu_predicted_values.reset_index(drop= True, inplace = True)

        alu_predicted_values['yhat1'] *= args['alu']
        total_product_values += alu_predicted_values['yhat1'].squeeze()
        
    # Predict st37 price if st37_weight is provided
    if 'st37' in args:
        st37_predicted_values, st37_full_projected_values = porphet_predict(model_name='st37',
                                                                            csv_file_name='st37',
                                                                            forecasting_period = forecasting_period)
        st37_predicted_values.reset_index(drop= True, inplace = True)
            
        # Adjust for the spot price if it is provided
        if 'p_st37' in args:
            st37_predicted_values = adjust_spot_price(st37_full_projected_values, args['p_st37']).tail(forecasting_period)
            st37_predicted_values.reset_index(drop= True, inplace = True)
            
        st37_predicted_values['yhat1'] *= args['st37']
        total_product_values += st37_predicted_values['yhat1'].squeeze()

    # Predict labour cost if labour_hours is provided
    if 'labour_hours' in args:
        labour_predicted_cost, labour_full_projected_values = porphet_predict(model_name='labor_cost',
                                                                              csv_file_name='labor_cost',
                                                                              forecasting_period = forecasting_period)
        labour_predicted_cost.reset_index(drop= True, inplace = True)

        labour_predicted_cost['yhat1'] *= args['labour_hours']
        total_product_values += labour_predicted_cost['yhat1']


    # Predict medium_carbon if labour_hours is provided
    if 'medium_carbon' in args:
        medium_carbon_predicted_cost, medium_carbon_full_projected_values = porphet_predict(model_name='medium_carbon',
                                                                                                csv_file_name='medium_carbon',
                                                                                                forecasting_period = forecasting_period)
        medium_carbon_predicted_cost.reset_index(drop= True, inplace = True)
        
        # Adjust for the spot price if it is provided
        if 'p_medium_carbon' in args:
            medium_carbon_predicted_cost = adjust_spot_price(medium_carbon_full_projected_values,
                                                             args['p_medium_carbon']).tail(forecasting_period)
            medium_carbon_predicted_cost.reset_index(drop= True, inplace = True)
        
        medium_carbon_predicted_cost['yhat1'] *= args['medium_carbon']
        total_product_values += medium_carbon_predicted_cost['yhat1']

    # Predict high_carbon if labour_hours is provided
    if 'high_carbon' in args:
        high_carbon_predicted_cost, high_carbon_full_projected_values = porphet_predict(model_name='high_carbon',
                                                                                        csv_file_name='high_carbon',
                                                                                        forecasting_period = forecasting_period)
        high_carbon_predicted_cost.reset_index(drop= True, inplace = True)
        # Adjust for the spot price if it is provided
        if 'p_high_carbon' in args:
            high_carbon_predicted_cost = adjust_spot_price(high_carbon_full_projected_values,
                                                           args['p_high_carbon']).tail(forecasting_period)
            high_carbon_predicted_cost.reset_index(drop= True, inplace = True)
        
        high_carbon_predicted_cost['yhat1'] *= args['high_carbon']
        total_product_values += high_carbon_predicted_cost['yhat1']

    # Predict nonalloy_cast if labour_hours is provided
    if 'nonalloy_cast' in args:
        nonalloy_cast_predicted_cost, nonalloy_full_projected_values = porphet_predict(model_name='nonalloy_cast',
                                                                                       csv_file_name='nonalloy_cast',
                                                                                       forecasting_period = forecasting_period)
        nonalloy_cast_predicted_cost.reset_index(drop= True, inplace = True)
        
        # Adjust for the spot price if it is provided
        if 'p_nonalloy_cast' in args:
            nonalloy_cast_predicted_cost = adjust_spot_price(nonalloy_full_projected_values,
                                                      args['p_nonalloy_cast']).tail(forecasting_period)
            nonalloy_cast_predicted_cost.reset_index(drop= True, inplace = True)
        
        nonalloy_cast_predicted_cost['yhat1'] *= args['nonalloy_cast']
        total_product_values += nonalloy_cast_predicted_cost['yhat1']

    # Predict grey_cast_iron if labour_hours is provided
    if 'grey_cast_iron' in args:
        grey_cast_iron_predicted_cost, grey_cast_full_projected_values = porphet_predict(model_name='grey_cast_iron',
                                                                                         csv_file_name='grey_cast_iron',
                                                                                         forecasting_period = forecasting_period)
        grey_cast_iron_predicted_cost.reset_index(drop= True, inplace = True)
        if 'p_grey_cast_iron' in args:
            grey_cast_iron_predicted_cost = adjust_spot_price(grey_cast_full_projected_values, args['p_grey_cast_iron']).tail(forecasting_period)
            grey_cast_iron_predicted_cost.reset_index(drop= True, inplace = True)
            print('hey')
        grey_cast_iron_predicted_cost['yhat1'] *= args['grey_cast_iron']
        total_product_values += grey_cast_iron_predicted_cost['yhat1']

    # Predict nodular_cast_iron if labour_hours is provided
    if 'nodular_cast_iron' in args:
        nodular_cast_iron_predicted_cost, nodular_cast_full_projected_values = porphet_predict(model_name='nodular_cast_iron',
                                                                                               csv_file_name='nodular_cast_iron',
                                                                                               forecasting_period=forecasting_period)
        nodular_cast_iron_predicted_cost.reset_index(drop= True, inplace = True)
        
        # Adjust for the spot price if it is provided
        if 'p_nodular_cast_iron' in args:
            nodular_cast_iron_predicted_cost = adjust_spot_price(nodular_cast_full_projected_values, args['p_nodular_cast_iron']).tail(forecasting_period)
            nodular_cast_iron_predicted_cost.reset_index(drop= True, inplace = True)
        
        nodular_cast_iron_predicted_cost['yhat1'] *= args['nodular_cast_iron']
        total_product_values += nodular_cast_iron_predicted_cost['yhat1']


    # Create a DataFrame with 'ds' column and 'total_product_value'
    total_product_df = pd.DataFrame({'ds': alu_predicted_values['ds'] if 'alu_predicted_values' in locals()
                                     else st37_predicted_values['ds'] if 'st37_predicted_values' in locals()
                                     else labour_predicted_cost['ds'] if 'labour_predicted_cost' in locals()
                                     else grey_cast_iron_predicted_cost['ds'] if 'grey_cast_iron_predicted_cost' in locals()
                                     else nodular_cast_iron_predicted_cost['ds'] if 'nodular_cast_iron_predicted_cost' in locals()
                                     else nonalloy_cast_predicted_cost['ds'] if 'nonalloy_cast_predicted_cost' in locals()
                                     else medium_carbon_predicted_cost['ds'] if 'medium_carbon_predicted_cost' in locals()
                                     else copper_predicted_values['ds'] if 'copper_predicted_values' in locals()
                                     else high_carbon_predicted_cost['ds'],
                                     'total_product_value': total_product_values})

    # Convert the 'ds' column to string format
    total_product_df['ds'] = total_product_df['ds'].dt.strftime('%Y-%m')

    # Convert the DataFrame to a dictionary format for API
    result_dict = total_product_df.to_dict(orient='records')
    return result_dict

def convert_json(df):
    json_data = {}
    for index, row in df.iterrows():
        # Format the date string
        date_str = row['ds'].strftime('%Y-%m')
        # Format the total product value
        value_str = f"{row['total_product_value']:.2f}"
        # Add to the dictionary
        json_data[date_str] = value_str
    # Convert the dictionary to JSON string
    json_str = json.dumps(json_data)
    print(json_str)
    return json_str
