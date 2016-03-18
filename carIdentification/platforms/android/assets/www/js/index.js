/**************************************************************************************************
                 SMART TOLL COLLECTION & SMART PARKING SYSTEM
****************************************************************************************************/ 
var pub_key = "pub-c-a1f796fb-1508-4c7e-9a28-9645035eee90"
var sub_key = "sub-c-d4dd77a4-1e13-11e5-9dcf-0619f8945a4f"
var userName,passWord

var app = {
/************************************************************************************************
    FUNCTION NAME : Initialize()
    DESCRIPTION   : Initialize the app 
************************************************************************************************/     
    initialize: function() {
        app.onDeviceReady();
    },
/**************************************************************************************************
    FUNCTION NAME : onDeviceReady()
    DESCRIPTION   : on receiving deviceready, set UI to REGISTER   
****************************************************************************************************/ 
    onDeviceReady: function() {
        app.pubNubInit()
    },
/**************************************************************************************************
    FUNCTION NAME : pubnubInit()
    DESCRIPTION   : initializes pubnub with keys
****************************************************************************************************/    
    pubNubInit: function() {
            pubnub = PUBNUB({publish_key: pub_key,subscribe_key: sub_key})
            app.register()
    },
/**************************************************************************************************
    DESCRIPTION : Message to Server 
***************************************************************************************************/
    loginData:{
        "userName":window.localStorage.getItem('usrnm'),"passWord":window.localStorage.getItem('pswd'),"requester":"APP"
    },
/**************************************************************************************************
    FUNCTION NAME : register()
    DESCRIPTION   : login to app with the username & password to start the app 
****************************************************************************************************/ 
    register: function() {
        $(document).ready(function(){              
            $('#usrsubmit').click(function(){  
                app.publish()
                $(':mobile-pagecontainer').pagecontainer('change', $('#mainpage'));
            })
        })
        app.subscribeStart()
    },
/**************************************************************************************************
    FUNCTION NAME : logout()
    DESCRIPTION   : logout from app and clears the locally stored username & password from the app 
****************************************************************************************************/ 
    logout: function(){
        $(document).ready(function(){              
            $('#logout').click(function(){  
                   localStorage.clear();
            })
        })
        $(':mobile-pagecontainer').pagecontainer('change', $('#login'));
        app.register()
    },
/**************************************************************************************************
    FUNCTION NAME : subscribeStart()
    DESCRIPTION   : subscribes to vehicle reg-num and provide Vehicle Info details 
****************************************************************************************************/
    subscribeStart: function(){         
        
        pubnub.subscribe({                                     
            channel : "trackerrfid-resp",
            message : function(message){
                console.log(message)
                document.getElementById('userInfo1').innerHTML = message.contactNum;
                document.getElementById('userInfo2').innerHTML = message.ownerName;
                document.getElementById('userInfo3').innerHTML = message.address;
                document.getElementById('userInfo4').innerHTML = message.emergencyNum1;
                document.getElementById('userInfo5').innerHTML = message.emergencyNum2;          
            },            
        })
    },
/**************************************************************************************************
    FUNCTION NAME : publish()
    DESCRIPTION   : publish the data to server 
****************************************************************************************************/
    publish: function() {
        pubnub.publish({                                    
            channel : "trackerapp-req",
            message : app.loginData,
            callback: function(m){ console.log(m) }
        })
    }
};
/**************************************************************************************************
    DESCRIPTION   : app initializing function
****************************************************************************************************/
app.initialize();
//End of the Program
