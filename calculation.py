from flask import Flask, Response
from flask import request
from flask import render_template
import json
from flask_cors import CORS
from process_latex import process_sympy
from flask.json import jsonify
from sympy.core.sympify import sympify
from sympy import Number, NumberSymbol, Symbol

from getidentifiers import Getidentifiers
import getidentifiers
import os
import re
import requests

from ppp_datamodel import Sentence, Request, Response
import latexformlaidentifiers


parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
os.environ['PPP_QUESTIONPARSING_GRAMMATICAL_CONFIG'] = os.path.dirname(os.path.abspath(__file__)) + '/ppp_questionparsing_grammatical/nlp_classical_config.json'
os.environ['PYWIKIBOT2_DIR'] = os.path.dirname(os.path.abspath(__file__)) + '/pywikibot'
from ppp_datamodel.communication import Request
from ppp_questionparsing_grammatical import RequestHandler
from getformula import FormulaRequestHandler
from getformula import HindiRequestHandler 
from latexformlaidentifiers import Formulacalculation, prepformula


def getlhsrhs(formula,ext):
    """
        Break the formula into lhs and rhs
    """
    global lhs
    global rhs    
    lhs,rhs=formula.split(ext,1)  
    
def makeidentifier(symbol,values): 
    """
        Make dictionary for Values of Symbol
    """   
    symvalue={}
    for i in symbol:              
        for j in values:           
            if i==Symbol(j):                
                value=values[j]                
                symvalue[i]=value 
                  
    return symvalue

def makeresponse(formul):
    """
        Make response for the API
    """
    try:
        reques=Formulacalculation(formul)                         
        global identifiers
        identifiers=reques.answer()
        
        if identifiers:
            listidentifiers=list(identifiers)
            
            newlist= []
            for item in listidentifiers:
                newlist.append(str(item))            
                
            newlist.append(dict(formula=formul))            
            json_data=json.dumps(newlist)
            response=jsonify(newlist)            
            response.status_code = 200             
            return response   
        else:
            response = jsonify(formul)
            response.status_code = 206  
            print(response)           
            return response
    except :
        response= jsonify("System is not able to find the result.")
        response.status_code = 202
        return response
    

app = Flask(__name__)    
CORS(app)

@app.route('/')
def my_form():
    return render_template("index.html")

@app.route('/getresponse', methods=['POST'])
def my_form_post():
    """
        Get formula from the user input and process it
        Return response
    """
    try:
        if request.form['formula']:            
            global formula                
            formula= request.form['formula']                                 
            global processedformula
            processedformula=latexformlaidentifiers.prepformula(formula)  
                 
            if formula is not None: 
                return makeresponse(processedformula)            
                
                
    except:
        response= jsonify("System is not able to find the result.")
        response.status_code = 202
        return response
        
            

    
@app.route('/getengformula', methods=['POST'])
def get_formula():
    """
        Get English question from the user parse it to Questionparsing module to get Triple
        Parse Triple (Subject, predicate, ?) to FormulaRequestHandler to get Formula from Wikidata
        Return response 
    """ 
       
    try:
        question=request.form['formula']    
            
        meas = {'accuracy': 0.5, 'relevance': 0.5}
        q = RequestHandler(Request(language="en",id=1,tree=Sentence(question),measures=meas))
        query = q.answer()   
                        
        reques= FormulaRequestHandler(query)         
        global formula        
        formula=reques.answer() 
        
        global processedformula
        processedformula=latexformlaidentifiers.prepformula(formula) 
        print(processedformula)             
        if not (formula.startswith("System")): 
            return makeresponse(processedformula)             
        else:           
             
            response= jsonify(formula)           
            response.status_code = 202
            print(response)
            return response
    except Exception : 
            response= jsonify("System is not able to find the result.")
            response.status_code = 202
            return response
            #return ("System is not able to find the result.") 
    
@app.route('/gethindiformula', methods=['POST'])
def get_hindiformula():
    """
        Get Hindi question from the user and apply regex to get subject and predicate
        Parse subject and predicate to HindiRequestHandler to get formula
        Return response
    """    
	
    try: 
        question=request.form['formula']        
        matchObj = re.match( r'(.*)की (.*?) .*', question, re.M|re.I)
        matchObj1 = re.match( r'(.*)के लिए (.*?) क्या है *', question, re.M|re.I) 
        matchObj2 = re.match( r'(.*)और (.*?) के बीच *', question, re.M|re.I)
        if matchObj:
            subject=matchObj.group(1)
            predicate=matchObj.group(2)  
            
        if matchObj1:
            subject=matchObj1.group(1)
            predicate=matchObj1.group(2)  

        if matchObj2:
            subject=matchObj2.group(1)
            predicate=matchObj2.group(2)          
         
        reques = HindiRequestHandler("hi",subject,predicate)
        global formula
        formula=reques.answer()
        global processedformula
        processedformula=latexformlaidentifiers.prepformula(formula)    
        print(processedformula)        
        if not (formula.startswith("System")): 
            return makeresponse(processedformula)             
        else:
            response= jsonify(formula)
            response.status_code = 202
            return response
    except Exception : 
            response= jsonify("System is not able to find the result.")
            response.status_code = 202
            return response
        

@app.route('/getfinalresult', methods=['POST'])
def my_form_json(): 
    """
        Get Values for the identifiers
        Return Calculated result 
    """ 
    
       
    try:   
        identifiers1 = request.data.decode('utf-8')    
        json1=json.loads(identifiers1)                      
        seprator= getidentifiers.formuladivision(formula)
        if seprator is not None:               
            lhsrhs= getlhsrhs(processedformula,seprator)            
            f=process_sympy(rhs)
            f1=process_sympy(lhs)
            latexlhs=sympify(f1)    
            l=sympify(f) 
            #print(l)
            symbolvalue=makeidentifier(identifiers,json1)           
            value=l.evalf(subs=symbolvalue)  
               
            return ("%s %s %.2e" % (latexlhs,seprator,value))
        else:
            l=sympify(formula)             
            value=l.evalf(subs=json1)
                
            return ("%.2e" % value)
            
    except Exception :             
            return ("System is not able to find the result.")   
  
if __name__ == '__main__':
    app.run(debug=True)
    #get_formula()
