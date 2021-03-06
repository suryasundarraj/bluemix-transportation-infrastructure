/**************************************************************************************************
                 SMART TOLL COLLECTION & SMART PARKING SYSTEM
****************************************************************************************************/ 
var lastbal = 0;
var wallet = 0;
var parkingCodes = {0: "available", 1: "occupied",2: "unavailable"}
var app = {
/************************************************************************************************
    FUNCTION NAME : Initialize()
    DESCRIPTION   : Initialize the app 
************************************************************************************************/   
    initialize: function() {
        this.bindEvents();
        $(window).on("navigate", function (event, data) {          
            event.preventDefault();      
        })
    },
/**************************************************************************************************
    FUNCTION NAME : showLoading()
    DESCRIPTION   : displays loading text while the app fetches data from server
****************************************************************************************************/ 
    showLoading: function(text) {
        $.mobile.loading("show", {
            text: text,
            textVisible: true,
            textonly: false
        });
    },
/**************************************************************************************************
    FUNCTION NAME : status()
    DESCRIPTION   : requests for parking status from server 
****************************************************************************************************/    
    status: function(message) {
        pubnub.publish({
            channel: "parkingapp-req",
            message: message,
            callback: function(m) {
                console.log(m)
            },
            error: function(err) {
                console.log(err)
            }
        })
    },
/**************************************************************************************************
    FUNCTION NAME : refreshStatus()
    DESCRIPTION   : refresh the parking status to current updated value
****************************************************************************************************/
    refreshStatus: function() {
        if (window.localStorage.getItem('ui') == 'DEFAULT') {
            app.status(app.getStatusMessage1)
        }
    },
/**************************************************************************************************
    FUNCTION NAME : register()
    DESCRIPTION   : register the vehicle reg number to server and start the app 
****************************************************************************************************/    
    register: function() {
        $(document).ready(function(){       
            $(':mobile-pagecontainer').pagecontainer('change', $('#appRegister'));        
            $('#vehicle-num-submit').click(function(){
                if ($('#numberVehicle').val() != '') {
                    window.localStorage.setItem('ui', 'DEFAULT')
                    window.localStorage.setItem('number', $('#numberVehicle').val())
                    window.location.reload()
                    app.render()    
                }
            })
        })
    },
/**************************************************************************************************
    FUNCTION NAME : startParking()
    DESCRIPTION   : select the parking lot to book it   
****************************************************************************************************/    
    startParking: function(e) {
        var lot = $(e.target).data().lot        
        app.status(
           {"requester":"APP","lotNumber":lot,"requestType":2,"requestValue":window.localStorage.getItem('number')}
           )
        app.showLoading("Waiting for confirmation...");
    },
    
/**************************************************************************************************
    DESCRIPTION : Message to Server 
***************************************************************************************************/
    getStatusMessage1:{
        "requester": "APP",
        "lotNumber": 0,
        "requestType": 1,
        "requestValue": 0
    },
    getStatusMessage2:{
        "vehicleNumber":window.localStorage.getItem('number'),"requester":"APP","requestType":0
    },
/**************************************************************************************************
    FUNCTION NAME : blockFunction()
    DESCRIPTION   : publishes block status to server 
****************************************************************************************************/
    blockFunction: function(){
        blockValue = 1
        window.localStorage.setItem('blockValue', blockValue)
        app.publish({"vehicleNumber":window.localStorage.getItem('number'),"requester":"APP","requestType":0,"requestValue":window.localStorage.getItem('blockValue')})
    },
/**************************************************************************************************
    FUNCTION NAME : unblockFunction()
    DESCRIPTION   : publishes unblock status to server
****************************************************************************************************/
    unblockFunction: function(){
        blockValue = 0
        window.localStorage.setItem('blockValue', blockValue)
        app.publish({"vehicleNumber":window.localStorage.getItem('number'),"requester":"APP","requestType":0,"requestValue":window.localStorage.getItem('blockValue')})
    },
/**************************************************************************************************
    FUNCTION NAME : closeBill()
    DESCRIPTION   : closes the bill and calls parkdefault function
****************************************************************************************************/
    closeBill: function() {
        app.parkdefault();
    },
/**************************************************************************************************
    FUNCTION NAME : bindEvents()
    DESCRIPTION   : Adds event listeners and initialize the pubnub
****************************************************************************************************/
    bindEvents: function() {
        document.addEventListener('deviceready', this.onDeviceReady, false);
        app.pubnubInit()
    },
/**************************************************************************************************
    FUNCTION NAME : onDeviceReady()
    DESCRIPTION   : on receiving deviceready, set UI to REGISTER   
****************************************************************************************************/   
    onDeviceReady: function() {
        app.receivedEvent('deviceready');
        if(window.localStorage.getItem('ui')) {
            window.localStorage.setItem('ui', 'REGISTER');
        }
    },
/**************************************************************************************************
    FUNCTION NAME : receivedEvents()
    DESCRIPTION   : listen for device to be ready 
****************************************************************************************************/
    receivedEvent: function(id) {
        var parentElement = document.getElementById(id);
        var listeningElement = parentElement.querySelector('.listening');
        var receivedElement = parentElement.querySelector('.received');
        listeningElement.setAttribute('style', 'display:none;');
        receivedElement.setAttribute('style', 'display:block;');
    },
/**************************************************************************************************
    FUNCTION NAME : pubnubInit()
    DESCRIPTION   : initializes pubnub with keys
****************************************************************************************************/
    pubnubInit: function() {
        pubnub = PUBNUB({                          
            publish_key   : 'pub-c-913ab39c-d613-44b3-8622-2e56b8f5ea6d',
            subscribe_key : 'sub-c-8ad89b4e-a95e-11e5-a65d-02ee2ddab7fe'})
        app.render()
    },
/**************************************************************************************************
    FUNCTION NAME : reset()
    DESCRIPTION   : resets the local storage(vehicle number)
****************************************************************************************************/
    reset: function() {
        pubnub.unsubscribe({
            channel: window.localStorage.getItem('number'),
        });
        setTimeout(function(){
            localStorage.clear();
        },10);
        app.render()
    },
/**************************************************************************************************
    FUNCTION NAME : addMoney()
    DESCRIPTION   : Adds money and provides popup notification for user
****************************************************************************************************/    
    addMoney: function(){
        var amt = document.getElementById("registerAmt").value;
        if(amt >= 100){
            document.getElementById('amtRe').innerHTML = "!!!HURRAY!!!<br>Your account has been recharged with &#8377;" + amt + "<br>··• )o( •··";    
            app.publish({"requester":"APP","requestType":1,"vehicleNumber":window.localStorage.getItem('number'),"rechargeAmt":amt})
        }
        else{
            document.getElementById('amtRe').innerHTML = "Minimum amount to recharge is &#8377; 100<br>*Please, enter the valid amount to recharge <br>··• )o( •··";
        }
    },
/**************************************************************************************************
    FUNCTION NAME : transactionStart()
    DESCRIPTION   : subscribes to vehicle reg-num and provide transaction history details 
****************************************************************************************************/
    transactionStart: function(){
        pubnub.subscribe({
            channel: window.localStorage.getItem('number')+window.localStorage.getItem('number'),
            message: function(m){
                $(document).ready(function(){
                    var tableNew = '<thead><tr><th><p>date/Time</p></th>' + 
                        '<th data-priority="1">Toll Name</th><th data-priority="2">Amt-Deducted' +
                        '</th><th data-priority="3">Amt-Added</th><th data-priority="3">Balance' +
                        '</th></tr></thead><tbody>'
                    for(var i = Object.keys(m).length - 1; i >= 0; i--){
                        tableNew += '<tr><th>'+ m[i][0] + '</th><td><b class="ui-table-cell-label">Toll Name</b>' + m[i][1] 
                        + '</td><td><b class="ui-table-cell-label">Amt-Deducted</b>' + m[i][2].toString() + '</td><td><b class="ui-table-cell-label">Amt-Added</b>' + 
                        m[i][3].toString() + '</td><td><b class="ui-table-cell-label">Balance</b>' + 
                        m[i][4].toString() + '</td></tr>';
                    };
                    tableNew += '</tbody>'
                    $('#transTable').html(tableNew);
                })
                },
                error: function (error) {
                  console.log(JSON.stringify(error));
                }
        })
        app.publish({"requester":"APP","requestType":2,"vehicleNumber":window.localStorage.getItem('number')});
    },
/**************************************************************************************************
    FUNCTION NAME : subscribeStart()
    DESCRIPTION   : subscribes to vehicle reg-num and provide Vehicle Info details 
****************************************************************************************************/
    subscribeStart: function(){         
        pubnub.subscribe({                                     
            channel : window.localStorage.getItem('number'),
            message : function(message){
                $.mobile.loading("hide");
                document.getElementById('userInfo').innerHTML = message.vehicleNumber;
                document.getElementById('userInfo1').innerHTML = message.ownerName;
                document.getElementById('userInfo2').innerHTML = message.vehicleType;
                document.getElementById('userInfo3').innerHTML = message.availableBal;
                
                if(message.warning != undefined || message.NHCrossed != undefined && message.dateTime != undefined && message.amtDeducted != undefined){
                    
                    if(message.warning.length > 10 && message.NHCrossed != undefined){
                        console.log(message.warning);
                        alert(message.warning + "\nSpotted near " + message.NHCrossed ) 
                    }
                    else if(message.warning.length > 10){
                        alert(message.warning)    
                    }
                    else if(message.dateTime1!=lastbal){
                        lastbal = message.dateTime1;
                        alert("You have been charged Rs.50 for using " + message.NHCrossed)
                    }
                    window.localStorage.setItem('localTollCross', message.NHCrossed)
                    window.localStorage.setItem('localDate', message.dateTime)
                    window.localStorage.setItem('localTime', message.dateTime1)
                    window.localStorage.setItem('localDeducted', message.amtDeducted)
                }
                document.getElementById('tollInfo').innerHTML = window.localStorage.getItem('localTollCross');
                document.getElementById('tollInfo1').innerHTML = window.localStorage.getItem('localDate');
                document.getElementById('tollInfo0').innerHTML = window.localStorage.getItem('localTime');
                document.getElementById('tollInfo2').innerHTML = window.localStorage.getItem('localDeducted');
            },            
            connect: function(){
                app.publish(app.getStatusMessage2);
            }
        })
    },
/**************************************************************************************************
    FUNCTION NAME : subscribeToStatus()
    DESCRIPTION   : shows the current parking lot status and adds class(available unavailable occupied) to it  
****************************************************************************************************/
    subscribeToStatus: function() {
        pubnub.subscribe({
            channel: "parkingapp-resp",
            message: function(message) {
                $.mobile.loading("hide");
                    Object.keys(message).forEach(function(lot){
                    $("div[data-lot="+lot+"]")
                    .removeClass("available unavailable occupied")
                    .addClass(parkingCodes[message[lot]])
                })
            },
            connect: function(){
                app.status(app.getStatusMessage1)
            }
        })
    },
/**************************************************************************************************
    FUNCTION NAME : subscribeToSelf()
    DESCRIPTION   : updates the parking lot occupied time and provides the notification of billing 
****************************************************************************************************/
    subscribeToSelf: function() {
      pubnub.subscribe({
        channel: window.localStorage.getItem('number'),
        message: function(message) {
            $.mobile.loading("hide");
            if (message.sessionType == 0) {
                window.localStorage.setItem('parking', JSON.stringify(message));
                key = 'parking'
                template = "#status-template"
                $("#parking-status").popup()
                var data = JSON.parse(window.localStorage.getItem(key))
                $('.status-content').empty()
                $('.status-content').append(Mustache.render($(template).html(), data))
                $( "#parking-status" ).popup( "open" )
                $('#parking-status-popup').removeClass('bill')
            } else {
                window.localStorage.setItem('bill', JSON.stringify(message));
                key = 'bill'
                template = "#bill-template"
                $("#parking-status").popup()
                var data = JSON.parse(window.localStorage.getItem(key))
                $('.status-content').empty()
                $('.status-content').append(Mustache.render($(template).html(), data))
                $( "#parking-status" ).popup( "open" )
                $('#parking-status-popup').addClass('bill')
            }
        },            
    })  
  },
/****************************************************************************************************************
    FUNCTION NAME : default()
    DESCRIPTION   : starts subscription and provides popups on recharging and on request for transaction history 
*****************************************************************************************************************/ 
    default: function() {
        app.showLoading("Fetching Current Status");
        app.subscribeStart();
        app.publish(app.getStatusMessage2);
        $(document).ready(function(){
            $(':mobile-pagecontainer').pagecontainer('change', $('#vehicleInfo'));
            $('#amountButton').on('click', function () {
                setTimeout(function () {
                    $('#addamtpop').popup('open', {
                    transition: 'pop'
                    });
                }, 1000);
            });
            $('#transactionButton').on('click', function () {
                setTimeout(function () {
                    $('#transaction').popup('open', {
                    transition: 'pop'
                    });
                }, 1000);
            });
        });
    },
/**************************************************************************************************
    FUNCTION NAME : render()
    DESCRIPTION   : checks for ui value and provides registration or call default()  
****************************************************************************************************/ 
    render: function() {
        if(!window.localStorage.getItem('ui')) {
            window.localStorage.setItem('ui', 'REGISTER');
        }
        switch(window.localStorage.getItem('ui')) {
            case 'REGISTER':
                app.register();
                break;
            default: 
                app.default();
        }
    },
/**************************************************************************************************
    FUNCTION NAME : parkdefault()
    DESCRIPTION   : refreshes the app and subscribes for the current parking status
****************************************************************************************************/
    parkdefault: function() {
        app.subscribeToStatus();
        $(document).on('resume', app.refreshStatus)
        $('.container').on('click', '.available', app.startParking)
        $('body').on('click', '.close-bill', app.closeBill)
        $( ":mobile-pagecontainer" ).pagecontainer( "change", $('#default'));
        app.showLoading("Fetching Current Status");
        app.subscribeToSelf();
        window.setTimeout(function(){
            app.status(app.getStatusMessage1)},2000);
    },
/**************************************************************************************************
    FUNCTION NAME : publish()
    DESCRIPTION   : publish the data to server 
****************************************************************************************************/
    publish: function(message) {
        pubnub.publish({                                    
            channel : "vehicleIdentificanApp-req",
            message : message,
            callback: function(m){ console.log(m) }
        })
    }
};
/**************************************************************************************************
    DESCRIPTION   : app initializing function
****************************************************************************************************/
app.initialize();

//End of the Program