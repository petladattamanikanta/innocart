/*
  UHF RFID Set/Get RFID Tx Power
 
 This example works only on the Arduino Mega 2560
 
 Serial port 1, connect to RFID module, baudrate = 115200
 Main Serial port, print Version msg, baudrate = 115200
 
 */
#define rfidSerial              Serial1

#define	RFID_FRAME_SOF1         0xA5
#define	RFID_FRAME_SOF2		0x5A
#define RFID_FRAME_EOF1		0x0D
#define RFID_FRAME_EOF2		0x0A

#define	RFID_FRAME_SOF_LEN	2
#define	RFID_FRAME_EOF_LEN	2
#define RFID_FRAME_LEN_LEN	2
#define	RFID_FRAME_CMD_LEN	1
#define	RFID_FRAME_CHK_LEN	1

#define RFID_FRAME_FIXED_LEN	(RFID_FRAME_SOF_LEN + RFID_FRAME_EOF_LEN + RFID_FRAME_LEN_LEN + RFID_FRAME_CMD_LEN + RFID_FRAME_CHK_LEN)

typedef enum
{
  RT_FALSE			 	 = 0,
  RT_TRUE			   	    ,
}
emReturnStateDef;

typedef struct
{
  byte			u8Sof1;			// header1
  byte			u8Sof2;			// header2
  byte			u8Len1;			// length
  byte			u8Len2;			// length
  byte 		        u8Cmd;			// cmd
  byte    		pData[250];
  byte                  u8Chk;			// CRC
  byte  		u8Eof1;			// end1
  byte			u8Eof2;			// end2
  byte			bCheckRet;
  byte       		bProcessing;
  byte       		bGetDataComplete;
}
stUartRecvFrameDef;

stUartRecvFrameDef stHostifRecvFrame;
byte u8HeadCnt = 0;	  // 帧头字节数
byte u8DataIdx = 0;	  // 接收帧数据索引
byte u8CalChk = 0;        // 计算校验值


// Calculate Frame check
byte Cal_Xor(byte *pBuf, int u16Len)
{
  byte	crc = 0;
  int	i;

  for (i=0; i<u16Len; i++)
  {
    crc ^= pBuf[i];
  }

  return crc;
}

// build rfid module communicate frame
int Build_RFID_Frame(byte u8Cmd, byte *pInData, int u16InLen, byte *pOutData, int *u16OutLen)
{
  int	cur = 0, i;

  /* frame header */
  pOutData[cur++] = RFID_FRAME_SOF1;
  pOutData[cur++] = RFID_FRAME_SOF2;
  /* length */
  pOutData[cur++] = ((u16InLen + RFID_FRAME_FIXED_LEN) >> 8) & 0xFF;
  pOutData[cur++] = (u16InLen + RFID_FRAME_FIXED_LEN) & 0xFF;
  /* cmd */
  pOutData[cur++] = u8Cmd;
  /* data */
  for (i=0; i<u16InLen; i++)
  {
    pOutData[cur++] = pInData[i];
  }
  /* frame check */
  pOutData[cur++] = Cal_Xor(&pOutData[2], (u16InLen+3));
  /* frame end */
  pOutData[cur++] = RFID_FRAME_EOF1;
  pOutData[cur++] = RFID_FRAME_EOF2;

  *u16OutLen = cur;

  return 0;
}

// serial send one frame data to rfid
void serialSendFrameToRFID(byte *sbuf, int len)
{
  rfidSerial.write(sbuf, len);
}

// Clear rfid serial buffer
void ClearrfidSerialReceiveBuffer(void)
{
  while(rfidSerial.read() >= 0) {
  }
}

// parse rfid frame
void Hostif_Parse_Frame(void)
{
  byte u8Data;

  if (rfidSerial.available() > 0)      // is receive data
  {	
    if (stHostifRecvFrame.bProcessing)
    {
      return;
    }

    u8Data = rfidSerial.read();

    if ( u8HeadCnt < 5 )				
    {
      switch (u8HeadCnt)	// get header data
      {
      case 0:																		// 帧头，高字节
        {
          if ( u8Data == RFID_FRAME_SOF1 )
          {
            u8HeadCnt++;
            stHostifRecvFrame.u8Sof1 	= u8Data;
          }
          break;		
        }
      case 1:																		// 帧头，低字节
        {
          if ( u8Data == RFID_FRAME_SOF2 )
          {
            u8HeadCnt++;
            stHostifRecvFrame.u8Sof2 = u8Data;
            u8CalChk = 0;
          }
          else
          {
            u8HeadCnt = 0;
          }
          break;		
        }

      case 2:																		// 帧长度，高字节
        {
          stHostifRecvFrame.u8Len1 = u8Data;
          u8HeadCnt++;
          u8CalChk 	^= u8Data;

          break;
        }

      case 3:																		// 帧长度，低字节
        {
          stHostifRecvFrame.u8Len2 = u8Data;
          u8HeadCnt++;
          u8CalChk ^= u8Data;	
          break;
        }

      case 4:																		// 帧类型
        {
          u8HeadCnt++;
          stHostifRecvFrame.u8Cmd = u8Data;
          u8CalChk ^= u8Data;

          u8DataIdx = 0;
          break;
        }
      }
    }
    else if (u8DataIdx < (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN))			// 帧数据
    {
      stHostifRecvFrame.pData[u8DataIdx++] = u8Data;
      u8CalChk ^= u8Data;
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN))			// CRC
    {
      if (u8CalChk != u8Data)									// check u8Data
      {
        u8HeadCnt = 0;
        u8CalChk = 0;
      }
      stHostifRecvFrame.u8Chk = u8Data;
      u8DataIdx++;
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN + 1))
    {
      if (u8Data == RFID_FRAME_EOF1)												// 帧尾，高字节
      {
        stHostifRecvFrame.u8Eof1 = u8Data;
        u8DataIdx++;
      }
      else
      {
        u8HeadCnt = 0;
        u8CalChk = 0;
      }
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN + 2))
    {
      if (u8Data == RFID_FRAME_EOF2)												// 帧尾，低字节
      {
        stHostifRecvFrame.u8Eof2 = u8Data;
        stHostifRecvFrame.bCheckRet = RT_TRUE;
        stHostifRecvFrame.bGetDataComplete = RT_TRUE; 		           
        stHostifRecvFrame.bProcessing = RT_TRUE;
      }
      else
      {
        stHostifRecvFrame.bCheckRet = RT_FALSE;
      }

      u8HeadCnt = 0;
      u8CalChk = 0;
      u8DataIdx	= 0;
    }
    else
    {
      u8HeadCnt = 0;
      u8CalChk = 0;
      u8DataIdx	= 0;
    }
  }
}

// handle
byte Rfid_Handle_Command(void)
{
  byte	ret = RT_FALSE;

  if((stHostifRecvFrame.bGetDataComplete == RT_TRUE) && (stHostifRecvFrame.bCheckRet == RT_TRUE))
  {
    switch (stHostifRecvFrame.u8Cmd)
    {
    case 0x01:		// Get Hardware Version response
      {
        break;
      }

    default:	//其它命令直接透传
      break;
    }

    ret = RT_TRUE;

    stHostifRecvFrame.bProcessing = RT_FALSE;
    stHostifRecvFrame.bGetDataComplete = RT_FALSE;
  }

  return ret;
}

// get hardware version
byte GetHardwareVersion(byte *ver)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x00, tmp, 0, sendbuf, &sendlen);      // cmd = 0x00
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x01)
      {
        memcpy(ver, stHostifRecvFrame.pData, 3);
        ret = RT_TRUE;
        break;
      }
    }
  }

  return ret;
}

// get firmware version
byte GetFirmwareVersion(byte *ver)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x02, tmp, 0, sendbuf, &sendlen);        // cmd = 0x02
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x03)
      {
        memcpy(ver, stHostifRecvFrame.pData, 3);
        ret = RT_TRUE;
        break;
      }
    }
  }

  return ret;
}

// set tx power
// antid: if antid = 0, The setting is valid for all antennas 
// rPow:  inventory power value
// wPow:  write, lock, kill operation power value
// saveflag: = 1, Save after power off, = 0, not save after power off
byte SetRFIDTxPower(byte antid, float rPow, float wPow, byte saveflag)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0, cur = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  tmp[cur++]  = (saveflag<<1);
  tmp[cur++]  = antid;
  tmp[cur++]  = (byte)((int)(rPow*100.0) >> 8);
  tmp[cur++]  = (byte)((int)(rPow*100.0) & 0xFF);
  tmp[cur++]  = (byte)((int)(wPow*100.0) >> 8);
  tmp[cur++]  = (byte)((int)(wPow*100.0) & 0xFF);
  Build_RFID_Frame(0x10, tmp, cur, sendbuf, &sendlen);        // cmd = 0x10 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x11)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)             // set ok
          ret = RT_TRUE;

        break;
      }
    }
  }

  return ret;
}

// get tx power
byte GetRFIDTxPower(byte *NumOfPort, float *rPow, float *wPow)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x12, tmp, cur, sendbuf, &sendlen);        // cmd = 0x12 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x13)
      {
        *NumOfPort = (stHostifRecvFrame.u8Len2 - 9) / 5;
        for (i=0; i<*NumOfPort; i++)
        {
          rPow[i] = (float)((stHostifRecvFrame.pData[(5*i) + 2] * 256) + stHostifRecvFrame.pData[(5*i) + 3])*0.01;
          wPow[i] = (float)((stHostifRecvFrame.pData[(5*i) + 4] * 256) + stHostifRecvFrame.pData[(5*i) + 5])*0.01;
        }

        ret = RT_TRUE;        
        break;
      }
    }
  }

  return ret;
}
//get region
//China1 0x01 
//China2 0x02 
//Europe 0x04
//USA 0x08 
//Korea 0x16
//Japan 0x32 
//Brazil 0x33
//WR1 0x34 
//South Africa 0x35
//Vietnam 0x36 
//INDIA 0x37
//TAIWAN 0x38 
//CHILE 0x39
//Uruguay 0x3A 
//Australia 0x3B
//New Zealand 0x3C 
//Europe 2 0x3D
byte SetRFIDRegion(byte region, byte saveflag) 
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x2C;
  tmp[cur++]  = saveflag;
  tmp[cur++]  = region;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x2C 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE;     
        }           
        break;
      }
    }
  }

  return ret;
}
//get region
//China1 0x01 
//China2 0x02 
//Europe 0x04
//USA 0x08 
//Korea 0x16
//Japan 0x32 
//Brazil 0x33
//WR1 0x34 
//South Africa 0x35
//Vietnam 0x36 
//INDIA 0x37
//TAIWAN 0x38 
//CHILE 0x39
//Uruguay 0x3A 
//Australia 0x3B
//New Zealand 0x3C 
//Europe 2 0x3D
byte GetRFIDRegion(byte *region)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x2E;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x2E 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          *region = stHostifRecvFrame.pData[1];
          ret = RT_TRUE;     
        }           
        break;
      }
    }
  }

  return ret;
}

// set Port Setting
byte SetPortSetting(byte *port, byte num, byte saveflag)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x28;
  tmp[cur++]  = saveflag;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;

  for (i = 0; i < num; i++) 
  {

    if (port[i] <= 8) {
      tmp[2] |= (1 << (port[i] - 1));
    } 
    else if (port[i] <= 16) {
      tmp[1] |= (1 << (port[i] - 8 - 1));
    } 
    else if (port[i] <= 24) {
      tmp[3] |= (1 << (port[i] - 16 - 1));
    } 
    else if (port[i] <= 32) {
      tmp[4] |= (1 << (port[i] - 24 - 1));
    } 
    else if (port[i] <= 40) {
      tmp[5] |= (1 << (port[i] - 32 - 1));
    } 
    else if (port[i] <= 48) {
      tmp[6] |= (1 << (port[i] - 40 - 1));
    } 
    else if (port[i] <= 56) {
      tmp[7] |= (1 << (port[i] - 48 - 1));
    } 
    else if (port[i] <= 64) {
      tmp[8] |= (1 << (port[i] - 56 - 1));
    }
  }

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x28
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE;     
        }           
        break;
      }
    }
  }

  return ret;
}

// Get Port Setting
byte GetPortSetting(byte *port, byte *num)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x2A;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x2A 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.u8Len2 == 0x0A)
        {
          unsigned int  porttmp = (stHostifRecvFrame.pData[0] << 8) + stHostifRecvFrame.pData[1];
          cur = 0;
          for (i=0; i<16; i++)
          {
            if ((porttmp & 0x01) == 0x01)
            {
              port[cur++] = (i+1);
            }
            porttmp = porttmp>>1;
          }
        }
        else
        {
          unsigned int  porttmp = (stHostifRecvFrame.pData[0] << 8) + stHostifRecvFrame.pData[1];
          cur = 0;
          for (i=0; i<16; i++)
          {
            if ((porttmp & 0x01) == 0x01)
            {
              port[cur++] = (i+1);
            }
            porttmp = porttmp>>1;
          }

          porttmp = ((stHostifRecvFrame.pData[3] << 8) + stHostifRecvFrame.pData[2]);
          for (i=0; i<16; i++)
          {
            if ((porttmp & 0x01) == 0x01)
            {
              port[cur++] = (i+1);
            }
            porttmp = porttmp>>1;
          }

          porttmp = ((stHostifRecvFrame.pData[5] << 8) + stHostifRecvFrame.pData[4]);
          for (i=0; i<16; i++)
          {
            if ((porttmp & 0x01) == 0x01)
            {
              port[cur++] = (i+1);
            }
            porttmp = porttmp>>1;
          }

          porttmp = ((stHostifRecvFrame.pData[7] << 8) + stHostifRecvFrame.pData[6]);
          for (i=0; i<16; i++)
          {
            if ((porttmp & 0x01) == 0x01)
            {
              port[cur++] = (i+1);
            }
            porttmp = porttmp>>1;
          }
        }
        *num  = cur;

        ret = RT_TRUE;         
        break;
      }
    }
  }

  return ret;
}

// Set Inventory Select Rule
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// saveflag: = 1, Save after power off, = 0, not save after power off
byte SetInventorySelectRule(byte mmb, int msa, int mdl, byte* mdata, byte saveflag)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x6E;
  tmp[cur++] = saveflag;
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x6E
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }
      
        break;
      }
    }
  }
  return ret;
}

// set query mode
// mode = 0, Multi tag mode
// mode = 1, Fast query tag mode
// mode = 2, Low power consumption
// mode = 3, Multi tag mode 2 (>300 tags)
// mode = 4, Adaptive mode(default)
byte SetQueryMode(byte mode, byte saveflag)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x76;
  tmp[cur++]  = saveflag;
  tmp[cur++] = mode;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x76
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE;     
        }           
        break;
      }
    }
  }

  return ret;
}

// Get query mode
// mode = 0, Multi tag mode
// mode = 1, Fast query tag mode
// mode = 2, Low power consumption
// mode = 3, Multi tag mode 2 (>300 tags)
// mode = 4, Adaptive mode(default)
byte GetQueryMode(byte *mode)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x78;
  tmp[cur++] = 0x00;
  tmp[cur++] = 0x00;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x78
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          *mode = stHostifRecvFrame.pData[1];
          ret = RT_TRUE; 
        }
      
        break;
      }
    }
  }

  return ret;
}

// single inventory, if query 1 tag success, then stop inventory
byte RFIDSingleInventory(byte *pc, byte *epc, float *rssi, byte *ant)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0, cur = 0, epclen, tidlen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  tmp[cur++] = 0x00;
  tmp[cur++] = 0x64;           
  Build_RFID_Frame(0x80, tmp, cur, sendbuf, &sendlen);
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x81)
      {
        memcpy(pc, stHostifRecvFrame.pData, 2);                  // 2 bytes
        epclen = (pc[0] >> 3) * 2;
        memcpy(epc, &stHostifRecvFrame.pData[2], epclen);        // epclen bytes
        memcpy(tmp, &stHostifRecvFrame.pData[2+epclen], 2);      // 2 bytes
        *rssi = (float)((tmp[0]*256 + tmp[1]) / 10.0);
        *ant = stHostifRecvFrame.pData[2+epclen+2];
        
        ret = RT_TRUE;
        break;
      }
      else if (stHostifRecvFrame.u8Cmd == 0xFF)
      {
        // inventory failed, return false.
        break;
      }
    }
  }

  return ret;
}

// start multiple inventory
// cnt = 0, multiple inventory forever
byte StartMultiInventory(byte cnt)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0;

  cmd = 0x82;
  tmp[cur++] = cnt>>8;
  tmp[cur++] = cnt;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x82
  serialSendFrameToRFID(sendbuf, sendlen);

  return ret;
}

// stop multiple inventory
byte StopMultiInventory(void)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x8C;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x8C
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        ret = RT_TRUE;     
        break;
      }
    }
  }

  return ret;
}

void ByteToHexStr(const unsigned char* source, char* dest, int sourceLen)
{
    short i;
    unsigned char highByte, lowByte;
 
    for (i = 0; i < sourceLen; i++)
    {
        highByte = source[i] >> 4;
        lowByte = source[i] & 0x0f ;
 
        highByte += 0x30;
 
        if (highByte > 0x39)
                dest[i * 2] = highByte + 0x07;
        else
                dest[i * 2] = highByte;
 
        lowByte += 0x30;
        if (lowByte > 0x39)
            dest[i * 2 + 1] = lowByte + 0x07;
        else
            dest[i * 2 + 1] = lowByte;
    }
    return ;
}

// Read Tag Memory 
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// mb,  read memory bank
// sa,  read start address
// dl,  read data length(word=16 bits)
// * readdata, read tag memory data
byte ReadTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte mb, int sa, int dl, byte* readdata)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x84;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = mb;
  tmp[cur++] = sa>>8;
  tmp[cur++] = sa;
  tmp[cur++] = dl>>8;
  tmp[cur++] = dl;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x84
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          memcpy(readdata, &stHostifRecvFrame.pData[4], dl*2);
          ret = RT_TRUE; 
        }
      
        break;
      }
    }
  }
  return ret;
}

// Write Tag Memory 
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// mb,  write memory bank
// sa,  write start address
// dl,  write data length(word=16 bits)
// data     write data
// flag 0--normal write, 1-- if tag is more than 1 tag, not write,
// if flag = 1, timeout is useful, it is timeout time ms
byte WriteTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte mb, int sa, int dl, byte* writedata, byte flag, int wtimeout)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x86;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = mb;
  tmp[cur++] = sa>>8;
  tmp[cur++] = sa;
  tmp[cur++] = dl>>8;
  tmp[cur++] = dl;
  bytelen = dl * 2;
  memcpy(&tmp[cur], writedata, bytelen);
  cur += bytelen;
  tmp[cur++] = flag;
  tmp[cur++] = wtimeout>>8;
  tmp[cur++] = wtimeout;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x86
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// Lock Tag Memory 
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// mb,  Lock memory bank, 0--Kill password bank; 1--Access password bank; 2--EPC; 3--TID; 4--USR
// flag 0--unlock, 1--lock,
byte LockTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte mb, byte flag)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x88;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  
  if (flag == 0)
  {
      switch(mb)
      {
          case 0:
                tmp[cur++] = 0x0C;
                tmp[cur++] = 0x00;
                tmp[cur++] = 0x00;
                break;
          case 1:
                tmp[cur++] = 0x03;
                tmp[cur++] = 0x00;
                tmp[cur++] = 0x00;
                break;
          case 2:
                tmp[cur++] = 0x00;
                tmp[cur++] = 0xC0;
                tmp[cur++] = 0x00;
                break;
          case 3:
                tmp[cur++] = 0x00;
                tmp[cur++] = 0x30;
                tmp[cur++] = 0x00;
                break;
          case 4:
                tmp[cur++] = 0x00;
                tmp[cur++] = 0x0C;
                tmp[cur++] = 0x00;
                break;
      }
  }
  else if (flag == 1)
  {
      switch(mb)
      {
          case 0:
                tmp[cur++] = 0x0C;
                tmp[cur++] = 0x02;
                tmp[cur++] = 0x00;
                break;
          case 1:
                tmp[cur++] = 0x03;
                tmp[cur++] = 0x00;
                tmp[cur++] = 0x80;
                break;
          case 2:
                tmp[cur++] = 0x00;
                tmp[cur++] = 0xC0;
                tmp[cur++] = 0x20;
                break;
          case 3:
                tmp[cur++] = 0x00;
                tmp[cur++] = 0x30;
                tmp[cur++] = 0x08;
                break;
          case 4:
                tmp[cur++] = 0x00;
                tmp[cur++] = 0x0C;
                tmp[cur++] = 0x02;
                break;
      }  
  }

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x89
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// Kill Tag 
// killpwd, kill password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
byte KillTag(byte* killpwd, byte mmb, int msa, int mdl, byte* mdata)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x8A;
  tmp[cur++] = killpwd[0];
  tmp[cur++] = killpwd[1];
  tmp[cur++] = killpwd[2];
  tmp[cur++] = killpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x8A
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// Block Write Tag Memory 
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// mb,  write memory bank
// sa,  write start address
// dl,  write data length(word=16 bits)
// data     write data
// flag 0--normal write, 1-- if tag is more than 1 tag, not write,
// if flag = 1, timeout is useful, it is timeout time ms
byte BlockWriteTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte mb, int sa, int dl, byte* writedata, byte flag, int wtimeout)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x93;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = mb;
  tmp[cur++] = sa>>8;
  tmp[cur++] = sa;
  tmp[cur++] = dl>>8;
  tmp[cur++] = dl;
  bytelen = dl * 2;
  memcpy(&tmp[cur], writedata, bytelen);
  cur += bytelen;
  tmp[cur++] = flag;
  tmp[cur++] = wtimeout>>8;
  tmp[cur++] = wtimeout;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x93
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// Block Erase Tag Memory 
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// mb,  write memory bank
// sa,  write start address
// dl,  write data length(word=16 bits)
byte BlockEraseTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte mb, int sa, int dl)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x95;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = mb;
  tmp[cur++] = sa>>8;
  tmp[cur++] = sa;
  tmp[cur++] = dl>>8;
  tmp[cur++] = dl;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x95
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// QT Set Para
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// qtData,  (bit0:0=Tag does not reduce range,1=Tag reduces range); (bit1: 0=Tag uses Private Memory Map, 1=Tag uses Public Memory Map), bit2-bit7 is RFU, set 0
byte QTSetPara(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte qtData)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x97;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = qtData;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x97
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// QT Get Para
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// *qtData,  (bit0:0=Tag does not reduce range,1=Tag reduces range); (bit1: 0=Tag uses Private Memory Map, 1=Tag uses Public Memory Map), bit2-bit7 is RFU, set 0
byte QTGetPara(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte* qtData)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x99;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x99
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          *qtData = stHostifRecvFrame.pData[1];
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// QT Read Tag Memory (private memory)
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// qtData,  (bit0:0=Tag does not reduce range,1=Tag reduces range); bit1-bit7 is RFU, set 0
// mb,  read memory bank
// sa,  read start address
// dl,  read data length(word=16 bits)
// * readdata, read tag memory data
byte QTReadTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte qtData, byte mb, int sa, int dl, byte* readdata)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x9B;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = qtData;
  tmp[cur++] = mb;
  tmp[cur++] = sa>>8;
  tmp[cur++] = sa;
  tmp[cur++] = dl>>8;
  tmp[cur++] = dl;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x9B
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          memcpy(readdata, &stHostifRecvFrame.pData[4], dl*2);
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// QT Write Tag Memory 
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// qtData,  (bit0:0=Tag does not reduce range,1=Tag reduces range); bit1-bit7 is RFU, set 0
// mb,  write memory bank
// sa,  write start address
// dl,  write data length(word=16 bits)
// writedata     write data
byte QTWriteTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte qtData, byte mb, int sa, int dl, byte* writedata)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x9D;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = qtData;
  tmp[cur++] = mb;
  tmp[cur++] = sa>>8;
  tmp[cur++] = sa;
  tmp[cur++] = dl>>8;
  tmp[cur++] = dl;
  bytelen = dl * 2;
  memcpy(&tmp[cur], writedata, bytelen);
  cur += bytelen;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x9D
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// BlockPermalock Tag Memory 
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// ReadLock,  bit0, 0=Read, 1=Permalock    bit1-bit7 is RFU, set 0
// mb,  memory bank, 0-RFU; 1-EPC; 2-TID; 3-User
// BlockPtr,  mask starting address, specified in units of 16 blocks
// BlockRange,  mask range, specified in units of 16 blocks
// mask     permalock bits (ReadLock=0 is read / ReadLock=1 is write)
byte BlockPermalockTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte ReadLock, byte mb, int BlockPtr, int BlockRange, byte* mask)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x9F;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = ReadLock;
  tmp[cur++] = mb;
  tmp[cur++] = BlockPtr>>8;
  tmp[cur++] = BlockPtr;
  tmp[cur++] = BlockRange>>8;
  tmp[cur++] = BlockRange;
  if (ReadLock == 1)
  {
      bytelen = BlockRange * 2;
      memcpy(&tmp[cur], mask, bytelen);
      cur += bytelen;
  }

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x9F
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          if (ReadLock == 0)
          {
              memcpy(mask, &stHostifRecvFrame.pData[2], (BlockRange * 2));
          }
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// Untraceable Tag Memory  (EPCglobal class 1 Gen2 V2.0 command)
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// rfu,  set 0
// u,  0: Deassert U in XPC_W1   1: Assert U in XPC_W1
// epc,  bit5 (show/hide): 0: show memory above EPC 1: hide memory above EPC   bit4-bit0 (length): New EPC length field (new L bits)
// tid,  0: hide none 1: hide some 2: hide all 
// user  0: view  1: hide
// range 0: normal 1: toggle temporarily 2: reduced 
byte UntraceableTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte rfu, byte u, byte epc, byte tid, byte user, byte range)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0xA1;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = rfu;
  tmp[cur++] = u;
  tmp[cur++] = epc;
  tmp[cur++] = tid;
  tmp[cur++] = user;
  tmp[cur++] = range;

  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0xA1
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

// Authenticate Tag Memory  (EPCglobal class 1 Gen2 V2.0 command)
// accpwd, access password
// mmb, select memory bank
// msa, select start address(bit)
// mdl, select data length(bit)
// mdata, select data 
// rfu,  set 0
// SenRep,  0: store  1: send
// IncRepLen,  0: Omit length from reply  1: Include length in reply
// CSI,  CSI
// Length   the message length in bits
// Message  includes parameters for the authentication, depends on CSI
// newMsg   the new Message tag reply
byte AuthenticateTagMemory(byte* accpwd, byte mmb, int msa, int mdl, byte* mdata, byte rfu, byte SenRep, byte IncRepLen, byte CSI, int Length, byte* Message, byte* newMsg)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, bytelen;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0xA3;
  tmp[cur++] = accpwd[0];
  tmp[cur++] = accpwd[1];
  tmp[cur++] = accpwd[2];
  tmp[cur++] = accpwd[3];
  tmp[cur++] = mmb;
  tmp[cur++] = msa>>8;
  tmp[cur++] = msa;
  tmp[cur++] = mdl>>8;
  tmp[cur++] = mdl;
  bytelen = (mdl + 7)/8;
  memcpy(&tmp[cur], mdata, bytelen);
  cur += bytelen;
  tmp[cur++] = rfu;
  tmp[cur++] = SenRep;
  tmp[cur++] = IncRepLen;
  tmp[cur++] = CSI;
  tmp[cur++] = Length>>8;
  tmp[cur++] = Length;
  bytelen = (Length + 7)/8;
  memcpy(&tmp[cur], Message, bytelen);
  cur += bytelen;
  
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0xA3
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
          memcpy(newMsg, &stHostifRecvFrame.pData[4], bytelen);
          ret = RT_TRUE; 
        }      
        break;
      }
    }
  }
  return ret;
}

void setup() {

  Serial.begin(115200);
  rfidSerial.begin(115200);

  Serial.println("Test inventory tag process, select rule set and clean function!");
  Serial.println("press 'S' Set Select rule");
  Serial.println("press 'C' clean Select rule");
}

void loop() {
  byte cmd, result;

  if ( Serial.available())
  {
      cmd = Serial.read();
      
      if (cmd == 'S')
      {
          byte mmb, mdata[100], readdata[100];
          int  msa, mdl, sa, dl;
          char tmp[100];
        
          mmb = 1;                      // EPC
          msa = 0x20F;                  // 0x20F   (nxp uhf tag PSF bit)
          mdl = 1;                      // 1 bit
          mdata[0] = 0x80;              // MSB first

          result = SetInventorySelectRule(mmb, msa, mdl, mdata, 1);      // saveflag = 1, only inventory PSF bit = 1 tag
          if (result == RT_TRUE)
          {
              Serial.println("Set Inventory Select Rule success!");    
          }
          else
          {
              Serial.println("Set Inventory Select Rule failed!");    
          }
      }
      else if (cmd == 'C')
      {
          byte mmb, mdata[100], readdata[100];
          int  msa, mdl, sa, dl;
          char tmp[100];
        
          mmb = 1;                      // EPC
          msa = 0x00;                   // 0x20F   (nxp uhf tag PSF bit)
          mdl = 0;                      // mdl = 0, means clean select rule
          mdata[0] = 0x00;              // MSB first

          result = SetInventorySelectRule(mmb, msa, mdl, mdata, 1);      // saveflag = 1, mdl = 0, means clean select rule
          if (result == RT_TRUE)
          {
              Serial.println("Clean Inventory Select Rule success!");    
          }
          else
          {
              Serial.println("Clean Inventory Select Rule failed!");    
          }
      }
  }  
}


