#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  8 14:37:27 2024

@author: salomeaubri
"""
import gurobipy as gb
from gurobipy import GRB
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import random
import os

from Step_3_Final import y_pred_gd, y_pred_closed

# Import price data
prices = pd.read_excel("C:/Users/leoni/Desktop/Machine Learning in Energy System/Assignment1_ML_in_Energy_Systems/Datasets/prices.xlsx")
prices = prices.rename(
    columns={
        "SpotPriceEUR": "Spot price",
        "BalancingPowerPriceUpEUR": "Up reg price",
        "BalancingPowerPriceDownEUR": "Down reg price",
    }
)

# Import actual power production
dataset = pd.read_csv("C:/Users/leoni/Desktop/Machine Learning in Energy System/Assignment1_ML_in_Energy_Systems/Datasets/Cumulative_dataset.csv")

# Parameters
TIME = range(566)  # Simpler range definition

# Choose the prediction model
prediction_model = "gradient_descent"  # Could be 'closed_form' or 'gradient_descent'
prediction = y_pred_gd if prediction_model == "gradient_descent" else y_pred_closed

farm_capacity = 6  # MW

# Initialize optimization model
model = gb.Model("optimization_model")
model.Params.TimeLimit = 100
model.setParam("NonConvex", 2)

# Define variables
bid = {t: model.addVar(lb=0, ub=farm_capacity, name=f"Wind power bid at time {t}") for t in TIME}
delta_plus = {t: model.addVar(lb=0, ub=gb.GRB.INFINITY, name=f"Positive difference at time {t}") for t in TIME}
delta_minus = {t: model.addVar(lb=0, ub=gb.GRB.INFINITY, name=f"Negative difference at time {t}") for t in TIME}

# Define objective function
DA_revenue = gb.quicksum(prices["Spot price"][t] * bid[t] for t in TIME)
balancing_revenue = gb.quicksum(
    prices["Down reg price"][t] * delta_plus[t] - prices["Up reg price"][t] * delta_minus[t] for t in TIME
)
model.setObjective(DA_revenue + balancing_revenue, GRB.MAXIMIZE)

# Define constraints
for t in TIME:
    model.addConstr(prediction[t] - bid[t] == delta_plus[t] - delta_minus[t], name=f"Prediction constraint at {t}")

# Optimize the model
model.optimize()

# Extract optimal bids
optimal_bid = {t: bid[t].x for t in TIME}

# Plot results
plt.figure(figsize=(10, 6))
TIME1 = range(100, 300)
plt.plot(TIME1, [prediction[t] for t in TIME1], label="Prediction", color="blue", marker="o")
plt.plot(TIME1, [optimal_bid[t] for t in TIME1], label="Optimal Bid", color="green", marker="x")
plt.xlabel("Time (hours)")
plt.ylabel("Power (MW)")
plt.title("Optimal Bids vs Predictions Over Time")
plt.legend()
plt.grid(True)
plt.show()

# Calculate actual revenue (real power production)
p_real = dataset['kalby_active_power'].tail(566).reset_index(drop=True)
spot_price = prices['Spot price'].tail(566).reset_index(drop=True)
UP_price = prices['Up reg price'].tail(566).reset_index(drop=True)
DW_price = prices['Down reg price'].tail(566).reset_index(drop=True)

# Calculate balance, DW, and UP
balance = {t: p_real[t] - optimal_bid[t] for t in TIME}
DW = {t: max(balance[t], 0) for t in TIME}  # Downward regulation
UP = {t: max(-balance[t], 0) for t in TIME}  # Upward regulation

# Calculate real DA and balancing revenue
DA_revenue = sum(spot_price[t] * optimal_bid[t] for t in TIME)
balancing_revenue = sum(
    DW_price[t] * DW[t] - UP_price[t] * UP[t] for t in TIME
)

# Print results
print(f"Day-Ahead Revenue: {DA_revenue}")
print(f"Balancing Revenue: {balancing_revenue}")
print(f"Real Revenue ({prediction_model}): {DA_revenue + balancing_revenue}")


### Maja's code

"""
def optimization(p_forecast):
        
        ###Model
    model = gb.Model()

        ###Parameters
    max_capacity = 1
    M = 4000
    hours = 24
    
    ###################
    #Decision variables
    ###################
    p_DA = model.addVars( #Power bid for day-ahead market
    hours, vtype=GRB.CONTINUOUS, name="p_DA"
    )

    aux_up = model.addVars( #Auxiliary varibale for linearizing. Called u_uparrow in the report
        hours, vtype=GRB.CONTINUOUS, name="aux_up"
    )

    aux_down = model.addVars( #Auxiliary varibale for linearizing. Called u_downarrow in the report
        hours, vtype=GRB.CONTINUOUS, name="aux_down"
    )

    psi_down = model.addVars( #Binary varibale for linearizing
        hours, vtype=GRB.BINARY, name="y"
    )

    psi_up = model.addVars( #Binary varibale for linearizing
        hours, vtype=GRB.BINARY, name="z"
    )

    ############
    #Constraints
    ############

    #Capacity limits of the WF
    model.addConstrs((p_DA[t] <= max_capacity) for t in range(hours))
    model.addConstrs((p_DA[t] >= 0) for t in range(hours))

    #Linearization aux_down
    model.addConstrs((-p_forecast[t] + p_DA[t] <= M*psi_down[t]) for t in range(hours) for t in range(hours))
    model.addConstrs((p_forecast[t] - p_DA[t] <= M*(1-psi_down[t])) for t in range(hours))
    model.addConstrs((aux_down[t]>=0) for t in range(hours))
    model.addConstrs((aux_down[t]>=p_forecast[t]-p_DA[t]) for t in range(hours))
    model.addConstrs((aux_down[t]<=M*(1-psi_down[t])) for t in range(hours))
    model.addConstrs((aux_down[t]<= (p_forecast[t]-p_DA[t])+M*psi_down[t]) for t in range(hours))

    #Linearization aux_up
    model.addConstrs((p_forecast[t] - p_DA[t] <= M*psi_up[t]) for t in range(hours))
    model.addConstrs((-p_forecast[t] + p_DA[t] <= M*(1-psi_up[t])) for t in range(hours))
    model.addConstrs((aux_up[t]>=0) for t in range(hours))
    model.addConstrs((aux_up[t]>=p_DA[t]-p_forecast[t]) for t in range(hours))
    model.addConstrs((aux_up[t]<=M*(1-psi_up[t])) for t in range(hours))
    model.addConstrs((aux_up[t]<= (p_DA[t]-p_forecast[t])+M*psi_up[t]) for t in range(hours))


    ####################
    # Objective function
    ####################
    model.setObjective(
        gb.quicksum(
        prices['Spot price'][t] * p_DA[t] + prices['Down reg price'][t] * aux_down[t] - prices['Up reg price'][t] * aux_up[t]
        for t in range(hours)
        ),
        sense=GRB.MAXIMIZE
    )

    model.optimize()

    p_DA_values = np.array([model.getVarByName(f"p_DA[{t}]").X for t in range(hours)])
    p_DA_values=np.round(p_DA_values,3) 

    revenue_expected = np.round(model.objVal,2) #Revenue assuming the forecast is 100% accurate. In the day-ahead the actual wind power is not known
    

    return p_DA_values, revenue_expected



p_DA_values_lin_closed, revenue_lin_closed = optimization(prediction)


for t in range(24):
    print(f'Hour {t}: Forecasted power = {round(prediction[t],3)}, Day Ahead Bid = {p_DA_values_lin_closed[t]}')


"""
